#!/bin/bash
set -e

CLUSTER_NAME="${cluster_name}"
LABELS='${jsonencode(labels)}'
TAINTS='${jsonencode(taints)}'

# Configure kubelet labels and taints
cat <<EOF > /etc/eks/bootstrap.sh
#!/bin/bash
/etc/eks/bootstrap.sh $CLUSTER_NAME --kubelet-extra-args "--node-labels=$LABELS --register-with-taints=$TAINTS"
EOF

chmod +x /etc/eks/bootstrap.sh
/etc/eks/bootstrap.sh $CLUSTER_NAME --kubelet-extra-args "--node-labels=$LABELS --register-with-taints=$TAINTS"