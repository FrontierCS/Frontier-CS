#include <bits/stdc++.h>
using namespace std;

static const int INF_INT = 1e9;

int N, M;
vector<string> S;

struct XorShift {
    uint64_t x;
    XorShift(uint64_t seed = 88172645463393265ull) : x(seed) {}
    uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    int nextInt(int l, int r) {
        return l + (int)(next() % (uint64_t)(r - l + 1));
    }
    double nextDouble() {
        return (next() >> 11) * (1.0 / 9007199254740992.0);
    }
};

int countMatches(const vector<string>& grid, const vector<string>& sList) {
    int n = (int)grid.size();
    int res = 0;
    for (const string &t : sList) {
        int k = (int)t.size();
        bool ok = false;

        // Horizontal
        for (int i = 0; i < n && !ok; i++) {
            for (int j = 0; j < n && !ok; j++) {
                bool good = true;
                for (int p = 0; p < k; p++) {
                    char g = grid[i][(j + p) % n];
                    if (g != t[p]) { good = false; break; }
                }
                if (good) { ok = true; break; }
            }
        }
        // Vertical
        for (int j = 0; j < n && !ok; j++) {
            for (int i = 0; i < n && !ok; i++) {
                bool good = true;
                for (int p = 0; p < k; p++) {
                    char g = grid[(i + p) % n][j];
                    if (g != t[p]) { good = false; break; }
                }
                if (good) { ok = true; break; }
            }
        }

        if (ok) res++;
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> M)) {
        return 0;
    }
    S.resize(M);
    for (int i = 0; i < M; i++) cin >> S[i];

    // Letter frequency across all strings
    array<int, 8> freq{};
    freq.fill(0);
    int maxLen = 0, minLen = 1000;
    for (int i = 0; i < M; i++) {
        for (char c : S[i]) freq[c - 'A']++;
        int L = (int)S[i].size();
        maxLen = max(maxLen, L);
        minLen = min(minLen, L);
    }
    vector<int> letters(8);
    iota(letters.begin(), letters.end(), 0);
    stable_sort(letters.begin(), letters.end(), [&](int a, int b){
        return freq[a] > freq[b];
    });
    char mostCommonLetter = char('A' + letters[0]);

    // Buckets by length
    vector<vector<int>> buckets(maxLen + 1);
    for (int i = 0; i < M; i++) {
        buckets[S[i].size()].push_back(i);
    }

    // Time control (approx)
    auto start = chrono::steady_clock::now();
    const int TIME_LIMIT_MS = 1900;

    XorShift rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    int bestC = -1;
    vector<string> bestGrid(N, string(N, mostCommonLetter));

    auto elapsed_ms = [&](){
        auto now = chrono::steady_clock::now();
        return (int)chrono::duration_cast<chrono::milliseconds>(now - start).count();
    };

    // Multiple runs with randomized order within length buckets
    while (elapsed_ms() < TIME_LIMIT_MS) {
        vector<int> order;
        order.reserve(M);
        for (int L = maxLen; L >= 0; L--) {
            if (buckets[L].empty()) continue;
            // shuffle bucket
            auto idxs = buckets[L];
            // custom shuffle using XorShift
            for (int i = (int)idxs.size() - 1; i > 0; i--) {
                int j = rng.nextInt(0, i);
                swap(idxs[i], idxs[j]);
            }
            for (int id : idxs) order.push_back(id);
        }

        vector<string> grid(N, string(N, '.'));

        for (int id : order) {
            const string &t = S[id];
            int k = (int)t.size();

            int bestNew = INF_INT;
            int bestOri = -1;
            int bestI = -1, bestJ = -1;

            // Horizontal
            for (int i = 0; i < N; i++) {
                for (int j = 0; j < N; j++) {
                    int newc = 0;
                    bool ok = true;
                    for (int p = 0; p < k; p++) {
                        int r = i;
                        int c = (j + p) % N;
                        char g = grid[r][c];
                        char ch = t[p];
                        if (g != '.' && g != ch) { ok = false; break; }
                        if (g == '.') newc++;
                    }
                    if (ok) {
                        if (newc < bestNew) {
                            bestNew = newc;
                            bestOri = 0;
                            bestI = i;
                            bestJ = j;
                            if (bestNew == 0) break; // cannot do better
                        }
                    }
                }
                if (bestNew == 0) break;
            }
            // Vertical
            if (bestNew > 0) { // only check if not zero already
                for (int j = 0; j < N; j++) {
                    for (int i = 0; i < N; i++) {
                        int newc = 0;
                        bool ok = true;
                        for (int p = 0; p < k; p++) {
                            int r = (i + p) % N;
                            int c = j;
                            char g = grid[r][c];
                            char ch = t[p];
                            if (g != '.' && g != ch) { ok = false; break; }
                            if (g == '.') newc++;
                        }
                        if (ok) {
                            if (newc < bestNew) {
                                bestNew = newc;
                                bestOri = 1;
                                bestI = i;
                                bestJ = j;
                                if (bestNew == 0) break; // cannot do better
                            }
                        }
                    }
                    if (bestNew == 0) break;
                }
            }

            if (bestOri != -1) {
                // place string
                if (bestOri == 0) {
                    int i = bestI, j = bestJ;
                    for (int p = 0; p < k; p++) {
                        int r = i;
                        int c = (j + p) % N;
                        if (grid[r][c] == '.') grid[r][c] = t[p];
                    }
                } else {
                    int i = bestI, j = bestJ;
                    for (int p = 0; p < k; p++) {
                        int r = (i + p) % N;
                        int c = j;
                        if (grid[r][c] == '.') grid[r][c] = t[p];
                    }
                }
            }
            if (elapsed_ms() >= TIME_LIMIT_MS) break;
        }

        // Fill remaining '.' with most common letter to potentially increase matches
        vector<string> filled = grid;
        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N; j++) {
                if (filled[i][j] == '.') filled[i][j] = mostCommonLetter;
            }
        }

        int c = countMatches(filled, S);
        if (c > bestC) {
            bestC = c;
            bestGrid = filled;
        }
    }

    for (int i = 0; i < N; i++) {
        cout << bestGrid[i] << "\n";
    }
    return 0;
}