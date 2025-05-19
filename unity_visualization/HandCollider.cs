using UnityEngine;

public class HandCollider : MonoBehaviour
{
    [Header("Hand Settings")"]
    [SerializeField] private float colliderRadius = 0.5f;
    [SerializeField] private LayerMask handLayer;
    
    private void Start()
    {
        // Add sphere collider if none exists
        SphereCollider collider = GetComponent<SphereCollider>();
        if (collider == null)
        {
            collider = gameObject.AddComponent<SphereCollider>();
        }
        
        // Configure collider
        collider.radius = colliderRadius;
        collider.isTrigger = true;
        
        // Set layer if specified
        if (handLayer != 0)
        {
            gameObject.layer = LayerMask.NameToLayer(handLayer.name);
        }
        
        // Tag as hand
        gameObject.tag = "Hand";
    }
}
