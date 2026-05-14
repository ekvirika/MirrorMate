using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class GameManager : MonoBehaviour
{
    [Header("Game Settings")]
    [SerializeField] private GameObject ballPrefab;
    [SerializeField] private float spawnInterval = 1f;
    [SerializeField] private float minSpawnInterval = 0.5f;
    [SerializeField] private float spawnIntervalDecrease = 0.05f;
    [SerializeField] private float timeToStart = 3f;
    
    [Header("UI Elements")]
    [SerializeField] private TextMeshProUGUI scoreText;
    [SerializeField] private TextMeshProUGUI countdownText;
    
    private float currentSpawnInterval;
    private float timeSinceLastSpawn;
    private int score;
    private bool gameStarted = false;
    private bool isCountingDown = false;
    private float countdownTime;
    
    void Start()
    {
        currentSpawnInterval = spawnInterval;
        timeSinceLastSpawn = currentSpawnInterval;
        score = 0;
        UpdateScoreDisplay();
        
        // Start countdown
        isCountingDown = true;
        countdownTime = timeToStart;
    }

    void Update()
    {
        if (isCountingDown)
        {
            countdownTime -= Time.deltaTime;
            if (countdownTime <= 0)
            {
                isCountingDown = false;
                gameStarted = true;
                countdownText.text = "";
            }
            else
            {
                countdownText.text = Mathf.Ceil(countdownTime).ToString();
            }
        }
        else if (gameStarted)
        {
            timeSinceLastSpawn += Time.deltaTime;
            
            if (timeSinceLastSpawn >= currentSpawnInterval)
            {
                SpawnBall();
                timeSinceLastSpawn = 0f;
                
                // Gradually decrease spawn interval (make game harder)
                if (currentSpawnInterval > minSpawnInterval)
                {
                    currentSpawnInterval -= spawnIntervalDecrease;
                    if (currentSpawnInterval < minSpawnInterval)
                        currentSpawnInterval = minSpawnInterval;
                }
            }
        }
    }

    public void AddPoints(int points)
    {
        score += points;
        UpdateScoreDisplay();
    }

    private void UpdateScoreDisplay()
    {
        if (scoreText != null)
        {
            scoreText.text = $"Score: {score}";
        }
    }

    private void SpawnBall()
    {
        if (ballPrefab != null)
        {
            GameObject ball = Instantiate(ballPrefab, Vector3.zero, Quaternion.identity);
            BallController ballController = ball.GetComponent<BallController>();
            if (ballController != null)
            {
                ballController.StartFalling();
            }
        }
    }

    public void RestartGame()
    {
        score = 0;
        UpdateScoreDisplay();
        gameStarted = false;
        isCountingDown = true;
        countdownTime = timeToStart;
        currentSpawnInterval = spawnInterval;
        
        // Destroy all balls
        GameObject[] balls = GameObject.FindGameObjectsWithTag("Ball");
        foreach (GameObject ball in balls)
        {
            Destroy(ball);
        }
    }
}
