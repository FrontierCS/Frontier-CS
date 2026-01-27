#include <bits/stdc++.h>
using namespace std;

uint64_t rng_state;

inline uint64_t rng64() {
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 9;
    return rng_state;
}

int BASE_STEPS_PER_CASE;

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    const int K = 240; // fixed size ensuring existence by extension argument
    const int W_BAD = 10;
    const int W_MISS = 5;
    const int W_COLOR = 1;

    vector<vector<char>> wanted(N + 1, vector<char>(N + 1, 0));
    for (int i = 0; i < M; ++i) {
        int u = A[i];
        int v = B[i];
        if (u > v) swap(u, v);
        wanted[u][v] = wanted[v][u] = 1;
    }

    vector<vector<int>> grid(K, vector<int>(K));
    vector<int> cellsCount(N + 1);
    vector<vector<int>> edgesCount(N + 1, vector<int>(N + 1));

    long long bestP = (1LL << 60);
    vector<vector<int>> bestGrid;

    int RESTARTS = 3;
    long long stepLimit = BASE_STEPS_PER_CASE;
    long long cap = 1LL * K * K * 80; // up to 80 moves per cell
    if (stepLimit > cap) stepLimit = cap;
    if (stepLimit < RESTARTS) stepLimit = RESTARTS;
    long long stepsPerAttempt = stepLimit / RESTARTS;
    if (stepsPerAttempt <= 0) stepsPerAttempt = 1;

    for (int attempt = 0; attempt < RESTARTS; ++attempt) {
        // Random initialization
        fill(cellsCount.begin(), cellsCount.end(), 0);
        for (int i = 0; i < K; ++i) {
            for (int j = 0; j < K; ++j) {
                int c = (int)(rng64() % N) + 1;
                grid[i][j] = c;
                cellsCount[c]++;
            }
        }

        int missingColorCount = 0;
        for (int c = 1; c <= N; ++c)
            if (cellsCount[c] == 0) ++missingColorCount;

        for (int i = 0; i <= N; ++i)
            fill(edgesCount[i].begin(), edgesCount[i].end(), 0);

        // Count adjacencies
        for (int i = 0; i < K; ++i) {
            for (int j = 0; j + 1 < K; ++j) {
                int a = grid[i][j];
                int b = grid[i][j + 1];
                if (a != b) {
                    if (a > b) swap(a, b);
                    edgesCount[a][b]++;
                }
            }
        }
        for (int i = 0; i + 1 < K; ++i) {
            for (int j = 0; j < K; ++j) {
                int a = grid[i][j];
                int b = grid[i + 1][j];
                if (a != b) {
                    if (a > b) swap(a, b);
                    edgesCount[a][b]++;
                }
            }
        }

        int badPairsCount = 0, missingEdgeCount = 0;
        for (int i = 1; i <= N; ++i) {
            for (int j = i + 1; j <= N; ++j) {
                if (wanted[i][j]) {
                    if (edgesCount[i][j] == 0) ++missingEdgeCount;
                } else {
                    if (edgesCount[i][j] > 0) ++badPairsCount;
                }
            }
        }

        long long P = 1LL * W_BAD * badPairsCount +
                      1LL * W_MISS * missingEdgeCount +
                      1LL * W_COLOR * missingColorCount;

        if (P < bestP) {
            bestP = P;
            bestGrid = grid;
        }
        if (P == 0) return grid;

        // Local search
        for (long long iter = 0; iter < stepsPerAttempt; ++iter) {
            int x = (int)(rng64() % K);
            int y = (int)(rng64() % K);
            int oldC = grid[x][y];
            int newC = (int)(rng64() % N) + 1;
            if (newC == oldC) continue;

            int pairU[8], pairV[8], pairDelta[8];
            int pairCnt = 0;

            auto recordPair = [&](int a, int b, int delta) {
                if (a == b) return;
                if (a > b) swap(a, b);
                for (int t = 0; t < pairCnt; ++t) {
                    if (pairU[t] == a && pairV[t] == b) {
                        pairDelta[t] += delta;
                        return;
                    }
                }
                pairU[pairCnt] = a;
                pairV[pairCnt] = b;
                pairDelta[pairCnt] = delta;
                ++pairCnt;
            };

            auto processNeighbor = [&](int nx, int ny) {
                int nb = grid[nx][ny];
                if (nb != oldC) recordPair(oldC, nb, -1);
                if (nb != newC) recordPair(newC, nb, +1);
            };

            if (x > 0) processNeighbor(x - 1, y);
            if (x + 1 < K) processNeighbor(x + 1, y);
            if (y > 0) processNeighbor(x, y - 1);
            if (y + 1 < K) processNeighbor(x, y + 1);

            int deltaColor = 0;
            if (cellsCount[oldC] == 1) ++deltaColor;
            if (cellsCount[newC] == 0) --deltaColor;

            int deltaBad = 0, deltaMissing = 0;
            for (int idx = 0; idx < pairCnt; ++idx) {
                int u = pairU[idx];
                int v = pairV[idx];
                int cntBefore = edgesCount[u][v];
                int cntAfter = cntBefore + pairDelta[idx];
                if (cntAfter < 0) cntAfter = 0; // safety

                if (wanted[u][v]) {
                    if (cntBefore == 0 && cntAfter > 0) --deltaMissing;
                    else if (cntBefore > 0 && cntAfter == 0) ++deltaMissing;
                } else {
                    if (cntBefore == 0 && cntAfter > 0) ++deltaBad;
                    else if (cntBefore > 0 && cntAfter == 0) --deltaBad;
                }
            }

            long long deltaP = 1LL * W_BAD * deltaBad +
                               1LL * W_MISS * deltaMissing +
                               1LL * W_COLOR * deltaColor;

            bool accept = false;
            if (deltaP <= 0) {
                accept = true;
            } else {
                int baseProb = 300; // 30% at start for small delta
                int currentBase = (int)((long long)baseProb * (stepsPerAttempt - iter) / stepsPerAttempt);
                if (currentBase < 0) currentBase = 0;
                int thresh = currentBase / (1 + (int)deltaP);
                if (thresh > 0) {
                    unsigned int r = (unsigned int)(rng64() % 1000);
                    if (r < (unsigned int)thresh) accept = true;
                }
            }

            if (!accept) continue;

            grid[x][y] = newC;
            cellsCount[oldC]--;
            cellsCount[newC]++;

            missingColorCount += deltaColor;
            badPairsCount += deltaBad;
            missingEdgeCount += deltaMissing;

            for (int idx = 0; idx < pairCnt; ++idx) {
                int u = pairU[idx], v = pairV[idx];
                edgesCount[u][v] += pairDelta[idx];
                if (edgesCount[u][v] < 0) edgesCount[u][v] = 0; // safety
            }

            P += deltaP;

            if (P < bestP) {
                bestP = P;
                bestGrid = grid;
            }
            if (P == 0) return grid;
        }
    }

    // Extra refinement from best found state
    grid = bestGrid;

    // Recompute all counts from scratch
    fill(cellsCount.begin(), cellsCount.end(), 0);
    for (int i = 0; i < K; ++i)
        for (int j = 0; j < K; ++j)
            cellsCount[grid[i][j]]++;

    int missingColorCount = 0;
    for (int c = 1; c <= N; ++c)
        if (cellsCount[c] == 0) ++missingColorCount;

    for (int i = 0; i <= N; ++i)
        fill(edgesCount[i].begin(), edgesCount[i].end(), 0);

    for (int i = 0; i < K; ++i) {
        for (int j = 0; j + 1 < K; ++j) {
            int a = grid[i][j];
            int b = grid[i][j + 1];
            if (a != b) {
                if (a > b) swap(a, b);
                edgesCount[a][b]++;
            }
        }
    }
    for (int i = 0; i + 1 < K; ++i) {
        for (int j = 0; j < K; ++j) {
            int a = grid[i][j];
            int b = grid[i + 1][j];
            if (a != b) {
                if (a > b) swap(a, b);
                edgesCount[a][b]++;
            }
        }
    }

    int badPairsCount = 0, missingEdgeCount = 0;
    for (int i = 1; i <= N; ++i) {
        for (int j = i + 1; j <= N; ++j) {
            if (wanted[i][j]) {
                if (edgesCount[i][j] == 0) ++missingEdgeCount;
            } else {
                if (edgesCount[i][j] > 0) ++badPairsCount;
            }
        }
    }

    long long P = 1LL * W_BAD * badPairsCount +
                  1LL * W_MISS * missingEdgeCount +
                  1LL * W_COLOR * missingColorCount;

    long long moreSteps = stepsPerAttempt * 2 + 1000;
    for (long long iter = 0; iter < moreSteps && P > 0; ++iter) {
        int x = (int)(rng64() % K);
        int y = (int)(rng64() % K);
        int oldC = grid[x][y];
        int newC = (int)(rng64() % N) + 1;
        if (newC == oldC) continue;

        int pairU[8], pairV[8], pairDelta[8];
        int pairCnt = 0;

        auto recordPair = [&](int a, int b, int delta) {
            if (a == b) return;
            if (a > b) swap(a, b);
            for (int t = 0; t < pairCnt; ++t) {
                if (pairU[t] == a && pairV[t] == b) {
                    pairDelta[t] += delta;
                    return;
                }
            }
            pairU[pairCnt] = a;
            pairV[pairCnt] = b;
            pairDelta[pairCnt] = delta;
            ++pairCnt;
        };

        auto processNeighbor = [&](int nx, int ny) {
            int nb = grid[nx][ny];
            if (nb != oldC) recordPair(oldC, nb, -1);
            if (nb != newC) recordPair(newC, nb, +1);
        };

        if (x > 0) processNeighbor(x - 1, y);
        if (x + 1 < K) processNeighbor(x + 1, y);
        if (y > 0) processNeighbor(x, y - 1);
        if (y + 1 < K) processNeighbor(x, y + 1);

        int deltaColor = 0;
        if (cellsCount[oldC] == 1) ++deltaColor;
        if (cellsCount[newC] == 0) --deltaColor;

        int deltaBad = 0, deltaMissing = 0;
        for (int idx = 0; idx < pairCnt; ++idx) {
            int u = pairU[idx];
            int v = pairV[idx];
            int cntBefore = edgesCount[u][v];
            int cntAfter = cntBefore + pairDelta[idx];
            if (cntAfter < 0) cntAfter = 0;

            if (wanted[u][v]) {
                if (cntBefore == 0 && cntAfter > 0) --deltaMissing;
                else if (cntBefore > 0 && cntAfter == 0) ++deltaMissing;
            } else {
                if (cntBefore == 0 && cntAfter > 0) ++deltaBad;
                else if (cntBefore > 0 && cntAfter == 0) --deltaBad;
            }
        }

        long long deltaP = 1LL * W_BAD * deltaBad +
                           1LL * W_MISS * deltaMissing +
                           1LL * W_COLOR * deltaColor;

        bool accept = false;
        if (deltaP <= 0) {
            accept = true;
        } else {
            int baseProb = 200;
            int currentBase = (int)((long long)baseProb * (moreSteps - iter) / moreSteps);
            if (currentBase < 0) currentBase = 0;
            int thresh = currentBase / (1 + (int)deltaP);
            if (thresh > 0) {
                unsigned int r = (unsigned int)(rng64() % 1000);
                if (r < (unsigned int)thresh) accept = true;
            }
        }

        if (!accept) continue;

        grid[x][y] = newC;
        cellsCount[oldC]--;
        cellsCount[newC]++;

        missingColorCount += deltaColor;
        badPairsCount += deltaBad;
        missingEdgeCount += deltaMissing;

        for (int idx = 0; idx < pairCnt; ++idx) {
            int u = pairU[idx], v = pairV[idx];
            edgesCount[u][v] += pairDelta[idx];
            if (edgesCount[u][v] < 0) edgesCount[u][v] = 0;
        }

        P += deltaP;
    }

    // Hopefully P == 0 now; even if not, return best effort
    return grid;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    const long long TOTAL_BUDGET = 20000000LL; // total steps budget heuristic
    BASE_STEPS_PER_CASE = (int)(TOTAL_BUDGET / max(1, T));
    if (BASE_STEPS_PER_CASE < 200000) BASE_STEPS_PER_CASE = 200000;

    rng_state = chrono::steady_clock::now().time_since_epoch().count();

    while (T--) {
        int N, M;
        cin >> N >> M;
        vector<int> A(M), B(M);
        for (int i = 0; i < M; ++i) {
            cin >> A[i] >> B[i];
        }

        vector<vector<int>> C = create_map(N, M, A, B);
        int K = (int)C.size();
        int P = K;
        cout << P << "\n";
        for (int i = 0; i < P; ++i) {
            cout << K << (i + 1 < P ? ' ' : '\n');
        }
        cout << "\n";
        for (int i = 0; i < K; ++i) {
            for (int j = 0; j < K; ++j) {
                if (j) cout << ' ';
                cout << C[i][j];
            }
            cout << "\n";
        }
    }
    return 0;
}