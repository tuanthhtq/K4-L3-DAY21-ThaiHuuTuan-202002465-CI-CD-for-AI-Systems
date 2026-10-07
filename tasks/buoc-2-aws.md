# Buoc 2 - AWS S3, IAM, EC2

Repo da chuyen sang S3 + EC2. Runbook nay dung AWS CLI, region mac dinh `ap-southeast-1`.

## 1. S3 va DVC

```powershell
$env:AWS_REGION = "ap-southeast-1"
$env:BUCKET = "income-lab-202002465-<unique-suffix>"
aws sts get-caller-identity
aws s3api create-bucket --bucket $env:BUCKET --region $env:AWS_REGION --create-bucket-configuration LocationConstraint=$env:AWS_REGION
aws s3api put-bucket-versioning --bucket $env:BUCKET --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket $env:BUCKET --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket $env:BUCKET --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

dvc init
dvc remote add -d labstore "s3://$env:BUCKET/dvc"
dvc add data/train_batch1.csv
dvc add data/holdout.csv
dvc add data/train_batch2.csv
dvc push
git add data/*.dvc .dvc/config .gitignore
git commit -m "feat: track datasets with DVC on S3"
```

AWS CLI credentials tu `aws configure` duoc DVC tu dong dung. Khong commit `~/.aws/credentials`.

## 2. IAM role cho EC2

EC2 dung instance role chi co quyen doc artifact. Tao trust policy `ec2-trust.json`, sau do tao role/profile trong IAM Console hoac CLI. Khong dat access key vao user data.

```powershell
Set-Content ec2-trust.json '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
@"
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:GetObject"],"Resource":"arn:aws:s3:::$($env:BUCKET)/artifacts/current/*"}]}
"@ | Set-Content ec2-s3-read.json
aws iam create-role --role-name income-api-ec2-role --assume-role-policy-document file://ec2-trust.json
aws iam put-role-policy --role-name income-api-ec2-role --policy-name read-income-artifact --policy-document file://ec2-s3-read.json
aws iam create-instance-profile --instance-profile-name income-api-ec2-profile
aws iam add-role-to-instance-profile --instance-profile-name income-api-ec2-profile --role-name income-api-ec2-role
```

## 3. IAM user cho GitHub Actions

Rubric yeu cau `STORAGE_CREDENTIALS`, nen dung mot IAM user rieng cho lab. Policy chi cho doc/ghi hai prefix `dvc/` va `artifacts/`:

```powershell
@"
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"s3:ListBucket","Resource":"arn:aws:s3:::$($env:BUCKET)","Condition":{"StringLike":{"s3:prefix":["dvc/*","artifacts/*"]}}},{"Effect":"Allow","Action":["s3:GetObject","s3:PutObject"],"Resource":["arn:aws:s3:::$($env:BUCKET)/dvc/*","arn:aws:s3:::$($env:BUCKET)/artifacts/*"]}]}
"@ | Set-Content github-s3-policy.json
aws iam create-user --user-name income-lab-github
aws iam put-user-policy --user-name income-lab-github --policy-name income-lab-s3 --policy-document file://github-s3-policy.json
aws iam create-access-key --user-name income-lab-github
```

Luu access key vao GitHub Secret ngay. Khong commit hoac chia se secret key. Production nen thay access key dai han bang GitHub OIDC.

## 4. EC2

Tao Ubuntu 22.04 instance `t3.micro`, gan instance profile `income-api-ec2-profile`, EBS encryption bat, IMDSv2 required. Neu khong co quyen SSM, lay AMI moi nhat bang EC2 API:

```powershell
$env:AMI = aws ec2 describe-images --owners 099720109477 --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" "Name=state,Values=available" --query "sort_by(Images,&CreationDate)[-1].ImageId" --output text
```

Security group: SSH chi tu IP quan tri; TCP `8080` chi mo cho client can goi API. Gan Elastic IP neu can IP co dinh.

```powershell
aws ec2 create-key-pair --key-name income-api-key --query KeyMaterial --output text | Set-Content -Encoding ascii income-api-key.pem
$env:SG_ID = aws ec2 create-security-group --group-name income-api-sg --description "Income API" --query GroupId --output text
$env:MY_IP = (Invoke-WebRequest -UseBasicParsing https://checkip.amazonaws.com).Content.Trim()
aws ec2 authorize-security-group-ingress --group-id $env:SG_ID --protocol tcp --port 22 --cidr "$env:MY_IP/32"
aws ec2 authorize-security-group-ingress --group-id $env:SG_ID --protocol tcp --port 8080 --cidr "0.0.0.0/0"
Start-Sleep -Seconds 10
$env:INSTANCE_ID = aws ec2 run-instances --image-id $env:AMI --instance-type t3.micro --key-name income-api-key --security-group-ids $env:SG_ID --iam-instance-profile Name=income-api-ec2-profile --metadata-options HttpTokens=required,HttpPutResponseHopLimit=1 --block-device-mappings '{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":16,"VolumeType":"gp3","Encrypted":true,"DeleteOnTermination":true}}' --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=income-api}]' --query Instances[0].InstanceId --output text
aws ec2 wait instance-running --instance-ids $env:INSTANCE_ID
$env:SERVER_HOST = aws ec2 describe-instances --instance-ids $env:INSTANCE_ID --query "Reservations[0].Instances[0].PublicIpAddress" --output text
```

Tren EC2 cai:

```bash
sudo apt update && sudo apt install -y python3-pip
pip3 install fastapi uvicorn scikit-learn joblib boto3
mkdir -p ~/models ~/src
```

Copy `src/serve.py`, tao `/etc/systemd/system/income-api.service`:

```ini
[Unit]
Description=Income Model Inference Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="ARTIFACT_BUCKET=YOUR_BUCKET"
ExecStart=/usr/bin/python3 /home/ubuntu/src/serve.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable income-api
sudo systemctl start income-api
```

`src/serve.py` tu dong tai `s3://YOUR_BUCKET/artifacts/current/model.joblib` bang IAM role.

## 5. GitHub Secrets

- `STORAGE_CREDENTIALS`: JSON `{"aws_access_key_id":"...","aws_secret_access_key":"..."}`.
- `ARTIFACT_BUCKET`: ten S3 bucket.
- `SERVER_HOST`: public IP/Elastic IP EC2.
- `SERVER_USER`: `ubuntu`.
- `SERVER_SSH_KEY`: private EC2 key.

Workflow dung AWS region `ap-southeast-1`; sua `env.AWS_REGION` trong `.github/workflows/cicd.yml` neu dung region khac.

## 6. Kiem tra

```powershell
aws s3 ls "s3://$env:BUCKET/dvc/"
aws s3 ls "s3://$env:BUCKET/artifacts/current/"
curl "http://EC2_IP:8080/healthz"
curl -Method Post "http://EC2_IP:8080/score" -ContentType "application/json" -Body '{"features":[28,2,14,2,11,0,1,0,0,45]}'
```

Loi service: `sudo journalctl -u income-api -n 50 --no-pager`. Nen bat CloudTrail cho API activity va CloudWatch metrics/logs; CloudTrail data events va EC2 detailed monitoring co the phat sinh phi. Sau khi chup anh, terminate EC2 va xoa tai nguyen khong con dung de tranh phi.
