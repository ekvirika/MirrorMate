using UnityEngine;

[RequireComponent(typeof(SphereCollider))]
public class HandCollider : MonoBehaviour
{
    [Header("Hand Settings")]
    [SerializeField] private float colliderRadius = 0.5f;
    [SerializeField] private string handLayerName = "Default";
    
    private void Start()
    {
        // Get or create sphere collider
        SphereCollider collider = GetComponent<SphereCollider>();
        if (collider == null)
        {
            collider = gameObject.AddComponent<SphereCollider>();
        }
        
        // Configure collider
        collider.radius = colliderRadius;
        collider.isTrigger = true;
        
        // Set layer if specified
        if (!string.IsNullOrEmpty(handLayerName))
        {
            int layer = LayerMask.NameToLayer(handLayerName);
            if (layer != 0)
            {
                gameObject.layer = layer;
            }
        }
        
        // Tag as hand
        gameObject.tag = "Hand";
    }
}
