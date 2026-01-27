#include <bits/stdc++.h>
using namespace std;

static inline long long ceil_div(long long a, long long b) {
    return (a + b - 1) / b;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;
    
    long long bestScore = LLONG_MAX;
    int bestR = 0, bestC = 0, bestK = 0;
    int bestTopColor = 0; // 0 => top black, 1 => top white
    int bestA1 = 0, bestA2 = 0;
    
    for (int t = 0; t < 2; ++t) {
        // t == 0: top sea is black, top islands are white (w-1), bottom islands are black (b-1)
        // t == 1: top sea is white, top islands are black (b-1), bottom islands are white (w-1)
        int sTop = (t == 0 ? w - 1 : b - 1);
        int sBot = (t == 0 ? b - 1 : w - 1);
        
        int a1_min = (sTop > 0 ? 1 : 0);
        int a2_min = (sBot > 0 ? 1 : 0);
        int a1_max = (sTop > 0 ? 2 * sTop - 1 : 0);
        int a2_max = (sBot > 0 ? 2 * sBot - 1 : 0);
        
        for (int a1 = a1_min; a1 <= a1_max; ++a1) {
            for (int a2 = a2_min; a2 <= a2_max; ++a2) {
                // Compute minimal columns C with a reserved connectivity column
                long long c1 = (sTop > 0 ? 1 + ceil_div(2LL * sTop, a1) : 1);
                long long c2 = (sBot > 0 ? 1 + ceil_div(2LL * sBot, a2) : 1);
                long long C = max({1LL, c1, c2});
                long long R = a1 + a2 + 2;
                if (R <= 0 || C <= 0) continue;
                if (R > 100000 || C > 100000) continue;
                if (R * C > 100000) continue;
                
                long long costPerCol;
                if (t == 0) { // top black
                    costPerCol = 1LL * x * (a1 + 1) + 1LL * y * (a2 + 1);
                } else { // top white
                    costPerCol = 1LL * x * (a2 + 1) + 1LL * y * (a1 + 1);
                }
                long long score = costPerCol * C; // constant part (x-y)*(b-w) ignored for comparison
                
                if (score < bestScore) {
                    bestScore = score;
                    bestR = (int)R;
                    bestC = (int)C;
                    bestK = a1 + 1;
                    bestTopColor = t;
                    bestA1 = a1;
                    bestA2 = a2;
                }
            }
        }
    }
    
    // Build the grid from best configuration
    int R = bestR, C = bestC, K = bestK;
    int t = bestTopColor;
    int a1 = bestA1, a2 = bestA2;
    int sTop = (t == 0 ? w - 1 : b - 1);
    int sBot = (t == 0 ? b - 1 : w - 1);
    
    char topColor = (t == 0 ? '@' : '.');
    char bottomColor = (t == 0 ? '.' : '@');
    char topIslandColor = (t == 0 ? '.' : '@');
    char bottomIslandColor = (t == 0 ? '@' : '.');
    
    vector<string> grid(R, string(C, bottomColor));
    for (int i = 0; i < K; ++i) grid[i].assign(C, topColor);
    
    int reservedCol = C - 1; // reserved connectivity column
    
    // Place islands in top sea (rows 0..K-2)
    int placed = 0;
    for (int i = 0; i < a1 && placed < sTop; ++i) {
        int row = i;
        int start = (i & 1);
        for (int col = start; col < C && placed < sTop; col += 2) {
            if (col == reservedCol) continue;
            grid[row][col] = topIslandColor;
            ++placed;
        }
    }
    
    // Place islands in bottom sea (rows K+1..R-1)
    placed = 0;
    for (int i = 0; i < a2 && placed < sBot; ++i) {
        int row = K + 1 + i;
        int start = (i & 1);
        for (int col = start; col < C && placed < sBot; col += 2) {
            if (col == reservedCol) continue;
            grid[row][col] = bottomIslandColor;
            ++placed;
        }
    }
    
    cout << R << " " << C << "\n";
    for (int i = 0; i < R; ++i) {
        cout << grid[i] << "\n";
    }
    return 0;
}