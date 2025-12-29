#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    const int TOTAL = 2 * N;
    const int MAXC = 100000;
    const int PERIM_LIMIT = 400000;
    const int HALF_PERIM_LIMIT = PERIM_LIMIT / 2; // 200000

    // Grid parameters
    const int S = 1000;       // cell size
    const int K = 100;        // number of cells per axis

    // Grid to store difference (#mackerels - #sardines)
    vector<vector<int>> grid(K, vector<int>(K, 0));

    for (int i = 0; i < TOTAL; i++) {
        int x, y;
        cin >> x >> y;
        int ix = min(x / S, K - 1);
        int iy = min(y / S, K - 1);
        if (i < N) grid[iy][ix] += 1;
        else grid[iy][ix] -= 1;
    }

    // Precompute left and right edge coordinates for each cell index
    vector<int> leftX(K), rightX(K), leftY(K), rightY(K);
    for (int i = 0; i < K; i++) {
        leftX[i] = i * S;
        leftY[i] = i * S;
        rightX[i] = (i == K - 1) ? MAXC : (i + 1) * S - 1;
        rightY[i] = (i == K - 1) ? MAXC : (i + 1) * S - 1;
    }

    long long bestSum = LLONG_MIN;
    int bestL = 0, bestR = 0, bestT = 0, bestB = 0;

    // Enumerate top and bottom rows
    for (int t = 0; t < K; t++) {
        vector<int> col(K, 0);
        for (int b = t; b < K; b++) {
            // Update column sums by adding row b
            for (int x = 0; x < K; x++) col[x] += grid[b][x];

            // Compute height and remaining allowable width
            int topCoord = leftY[t];
            int botCoord = rightY[b];
            int height = botCoord - topCoord;
            int rem = HALF_PERIM_LIMIT - height;
            if (rem < 0) break; // further increasing b only increases height

            // Prefix sums over columns
            vector<long long> P(K + 1, 0);
            for (int i = 0; i < K; i++) P[i + 1] = P[i] + col[i];

            deque<pair<int, long long>> dq; // (index L, P[L])
            for (int R = 0; R < K; R++) {
                // push P[R] as candidate L
                while (!dq.empty() && dq.back().second >= P[R]) dq.pop_back();
                dq.emplace_back(R, P[R]);

                long long T = (long long)rightX[R] - rem; // leftEdge >= T
                int Lmin;
                if (T <= 0) Lmin = 0;
                else Lmin = (int)((T + S - 1) / S); // ceil(T / S)

                if (Lmin > R) {
                    while (!dq.empty() && dq.front().first < Lmin) dq.pop_front();
                    continue;
                } else {
                    while (!dq.empty() && dq.front().first < Lmin) dq.pop_front();
                    if (dq.empty()) continue;
                    long long curr = P[R + 1] - dq.front().second;
                    if (curr > bestSum) {
                        bestSum = curr;
                        bestL = dq.front().first;
                        bestR = R;
                        bestT = t;
                        bestB = b;
                    }
                }
            }
        }
    }

    // If bestSum <= 0, fallback to full area rectangle covering all points
    if (bestSum <= 0) {
        cout << 4 << "\n";
        cout << 0 << " " << 0 << "\n";
        cout << MAXC << " " << 0 << "\n";
        cout << MAXC << " " << MAXC << "\n";
        cout << 0 << " " << MAXC << "\n";
        return 0;
    }

    // Output the best rectangle found
    int xL = leftX[bestL];
    int xR = rightX[bestR];
    int yT = leftY[bestT];
    int yB = rightY[bestB];

    // Safety: ensure perimeter constraint (should hold by construction)
    long long width = (long long)xR - xL;
    long long height = (long long)yB - yT;
    long long perim = 2 * (width + height);
    if (perim > PERIM_LIMIT) {
        // Fallback just in case (shouldn't happen)
        cout << 4 << "\n";
        cout << 0 << " " << 0 << "\n";
        cout << MAXC << " " << 0 << "\n";
        cout << MAXC << " " << MAXC << "\n";
        cout << 0 << " " << MAXC << "\n";
        return 0;
    }

    cout << 4 << "\n";
    cout << xL << " " << yT << "\n";
    cout << xR << " " << yT << "\n";
    cout << xR << " " << yB << "\n";
    cout << xL << " " << yB << "\n";
    return 0;
}