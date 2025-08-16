#!/usr/bin/env bash
set -euo pipefail

# This script checks for IOMMU support, which is crucial for DMA security.
# It checks for kernel parameters and the existence of IOMMU groups in sysfs.

ok=0
if grep -Eq 'intel_iommu=on|amd_iommu=on' /proc/cmdline; then
    ok=1
    echo "[info] IOMMU kernel parameter detected."
fi

if [ -d /sys/kernel/iommu_groups ] && [ "$(ls -A /sys/kernel/iommu_groups)" ]; then
    ok=1
    echo "[info] IOMMU groups found in sysfs."
fi

if [ $ok -eq 1 ]; then
  echo "[ok] IOMMU is likely enabled, providing stronger DMA isolation."
  exit 0
else
  echo "::warning:: IOMMU not detected or enabled. DMA isolation may be reduced."
  echo "To enable, add 'intel_iommu=on' or 'amd_iommu=on' to your kernel boot parameters."
  exit 1
fi
