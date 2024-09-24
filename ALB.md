# recommend 서비스 ALB로 배포하기.

## 1.정책 생성.

curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.8.1/docs/install/iam_policy.json

aws iam create-policy \
 --policy-name AWSLoadBalancerControllerIAMPolicy \
 --policy-document file://iam_policy.json

해당 링크의 정책을 다운로드 하여 iam_policy.json 파일 생성.

## 2. 내 계정정보를 설정

내 계정정보 조회 : aws sts get-caller-identity
export CLUSTER_NAME=<내 클러스터 이름>
export ACCOUNT_ID=<내계정ID>
export VPC_ID=<EKS설치된 vpc의 ID>
export REGION=ap-northeast-2

## 3. OIDC 활성화

eksctl utils associate-iam-oidc-provider --cluster $CLUSTER_NAME --approve
IAM Identity providers에 Provider 생성됨

## 4. IAMserviceaccount를 만들어서 해당 IAM롤 부여.

eksctl create iamserviceaccount --cluster=$CLUSTER_NAME   --namespace=kube-system   --name=aws-load-balancer-controller   --role-name AmazonEKSLoadBalancerControllerRole   --attach-policy-arn=arn:aws:iam::$ACCOUNT_ID:policy/AWSLoadBalancerControllerIAMPolicy --override-existing-serviceaccounts --approve

AmazonEKSLoadBalancerControllerRole 역할, serviceaccount 생성 및 정책부여

## 5. 로드밸런서 컨트롤러 생성 (helm) 및 설치

curl https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 > get_helm.sh
chmod 700 get_helm.sh
./get_helm.sh
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
 -n kube-system \
 --set clusterName=$CLUSTER_NAME \
	--set serviceAccount.create=false \
	--set serviceAccount.name=aws-load-balancer-controller \
	--set image.repository=602401143452.dkr.ecr.ap-northeast-2.amazonaws.com/amazon/aws-load-balancer-controller \
	--set region=ap-northeast-2 \
	--set vpcId=$VPC_ID

kube-system 네임스페이스에 IAMSA를 가진 파드2개가 생성되었고, sa에 ingress가 생성되면 aws의 ALB를 생성할수 있는 역할이 있음.

## 6. ingress 생성

ingress.yaml을 통해서 ingress생성
deployment, service 생성
