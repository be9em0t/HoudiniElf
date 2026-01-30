using System.Collections.Generic;
using UnityEngine;

[ExecuteAlways]
[AddComponentMenu("Unity-6/Duplicate Rotation To Children")]
public class DuplicateRotationToChildren : MonoBehaviour
{
    [Tooltip("If null, uses this GameObject as rotation source.")]
    public Transform source;

    [Tooltip("Copy localRotation (true) or world rotation (false).")]
    public bool useLocalRotation = true;

    [Tooltip("Keep initial offset of each child relative to source.")]
    public bool maintainOffset = true;

    [Tooltip("Include inactive children.")]
    public bool includeInactive = false;

    [Tooltip("If true, affects all descendants. If false, only direct children.")]
    public bool recursive = true;

    // cached offsets per child (child -> offset)
    private Dictionary<Transform, Quaternion> offsets = new Dictionary<Transform, Quaternion>();

    void Start() => RecalculateOffsets();

    void OnValidate() => RecalculateOffsets();

    [ContextMenu("Recalculate Offsets")]
    public void RecalculateOffsets()
    {
        offsets.Clear();
        var src = source ? source : transform;
        var children = recursive ? src.GetComponentsInChildren<Transform>(includeInactive) : GetDirectChildren(src);

        foreach (var child in children)
        {
            if (child == src) continue;
            if (!includeInactive && !child.gameObject.activeInHierarchy) continue;

            Quaternion offset = useLocalRotation
                ? child.localRotation * Quaternion.Inverse(src.localRotation)
                : child.rotation * Quaternion.Inverse(src.rotation);

            offsets[child] = offset;
        }
    }

    IEnumerable<Transform> GetDirectChildren(Transform t)
    {
        for (int i = 0; i < t.childCount; i++) yield return t.GetChild(i);
    }

    void LateUpdate()
    {
        var src = source ? source : transform;
        if (offsets.Count == 0) RecalculateOffsets();

        // iterate a snapshot of keys to avoid modification issues
        var keys = new List<Transform>(offsets.Keys);
        foreach (var child in keys)
        {
            if (child == null) continue;
            if (!includeInactive && !child.gameObject.activeInHierarchy) continue;

            if (!offsets.ContainsKey(child))
            {
                // new child added at runtime: compute and store offset
                Quaternion off = useLocalRotation
                    ? child.localRotation * Quaternion.Inverse(src.localRotation)
                    : child.rotation * Quaternion.Inverse(src.rotation);
                offsets[child] = off;
            }

            var offVal = offsets[child];
            if (maintainOffset)
            {
                if (useLocalRotation) child.localRotation = src.localRotation * offVal;
                else child.rotation = src.rotation * offVal;
            }
            else
            {
                if (useLocalRotation) child.localRotation = src.localRotation;
                else child.rotation = src.rotation;
            }
        }
    }
}