using UnityEngine;

public class BallController : MonoBehaviour
{
    [Header("Ball Settings")]
    [SerializeField] private float fallSpeed = 3f;
    [SerializeField] private float minSpawnX = -5f;
    [SerializeField] private float maxSpawnX = 5f;
    [SerializeField] private float spawnY = 10f;
    [SerializeField] private float minSize = 0.5f;
    [SerializeField] private float maxSize = 1.5f;
    [SerializeField] private float destroyY = -5f;
    
    [Header("Scoring")]
    [SerializeField] private int pointsPerCatch = 10;
    [SerializeField] private GameObject scoreDisplay;
    
    private float currentSpeed;
    private float currentSize;
    private bool isFalling = false;
    private GameManager gameManager;

    void Start()
    {
        // Randomize ball properties
        currentSpeed = fallSpeed * UnityEngine.Random.Range(0.8f, 1.2f);
        currentSize = UnityEngine.Random.Range(minSize, maxSize);
        transform.localScale = Vector3.one * currentSize;
        
        // Position ball at random x position
        float randomX = UnityEngine.Random.Range(minSpawnX, maxSpawnX);
        transform.position = new Vector3(randomX, spawnY, 0);
        
        // Find and reference the game manager
        gameManager = FindObjectOfType<GameManager>();
    }

    void Update()
    {
        if (isFalling)
        {
            // Move ball downwards
            transform.Translate(Vector3.down * currentSpeed * Time.deltaTime);
            
            // Destroy ball if it falls too low
            if (transform.position.y < destroyY)
            {
                Destroy(gameObject);
            }
        }
    }

    public void StartFalling()
    {
        isFalling = true;
    }

    private void OnTriggerEnter(Collider other)
    {
        // Check if we hit a hand
        if (other.CompareTag("Hand"))
        {
            // Add points
            if (gameManager != null)
            {
                gameManager.AddPoints(pointsPerCatch);
            }
            
            // Play catch sound
            AudioSource audio = GetComponent<AudioSource>();
            if (audio != null)
            {
                audio.Play();
            }
            
            // Destroy the ball
            Destroy(gameObject);
        }
    }
}
