#!/usr/bin/env bash
set -euo pipefail

ok=0

# Check kernel command line for IOMMU flags
if grep -Eq 'intel_iommu=on|amd_iommu=on' /proc/cmdline; then
    ok=1
fi

# Check if IOMMU groups exist and are non-empty
if [ -d /sys/kernel/iommu_groups ]; then
    if [ "$(ls -1 /sys/kernel/iommu_groups | wc -l)" -gt 0 ]; then
        ok=1
    fi
fi

# Additional check: look for IOMMU devices
if [ -e /sys/class/iommu ]; then
    ok=1
fi

if [ $ok -eq 1 ]; then
    echo "[ok] IOMMU likely enabled (isolation stronger)."
else
    echo "::warning:: IOMMU not detected; DMA isolation reduced."
    echo "To enable IOMMU, add intel_iommu=on or amd_iommu=on to kernel parameters"
fi
