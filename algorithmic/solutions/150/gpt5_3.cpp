#include <bits/stdc++.h>
using namespace std;

struct XorShift64 {
    uint64_t x;
    XorShift64(uint64_t seed = 88172645463393265ull) { if (seed) x = seed; else x = 88172645463393265ull; }
    inline uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline int nextInt(int mod) { return (int)(next() % mod); }
    inline double nextDouble() { return (next() >> 11) * (1.0 / (1ull << 53)); }
};

struct Candidate {
    bool ok;
    bool horiz;
    int i, j;
    int matches;
    int newAssigns;
    int score;
    Candidate() : ok(false), horiz(true), i(0), j(0), matches(0), newAssigns(0), score(INT_MIN) {}
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    vector<string> S(M);
    for (int i = 0; i < M; ++i) cin >> S[i];
    vector<int> L(M);
    for (int i = 0; i < M; ++i) L[i] = (int)S[i].size();

    const auto startTime = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.90; // seconds

    XorShift64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    auto countMatches = [&](const vector<vector<char>>& G)->int {
        // Build row and column strings and extended versions for wrap-around
        vector<string> row(N), col(N), rowE(N), colE(N);
        for (int i = 0; i < N; ++i) {
            row[i].resize(N);
            for (int j = 0; j < N; ++j) row[i][j] = G[i][j];
            rowE[i] = row[i] + row[i];
        }
        for (int j = 0; j < N; ++j) {
            col[j].resize(N);
            for (int i = 0; i < N; ++i) col[j][i] = G[i][j];
            colE[j] = col[j] + col[j];
        }
        int count = 0;
        for (int idx = 0; idx < M; ++idx) {
            const string &t = S[idx];
            int k = (int)t.size();
            bool ok = false;
            // rows
            for (int i = 0; i < N && !ok; ++i) {
                // check occurrences starting at positions 0..N-1 in rowE[i]
                const string &E = rowE[i];
                for (int st = 0; st < N; ++st) {
                    bool match = true;
                    for (int p = 0; p < k; ++p) {
                        if (E[st + p] != t[p]) { match = false; break; }
                    }
                    if (match) { ok = true; break; }
                }
            }
            // cols
            for (int j = 0; j < N && !ok; ++j) {
                const string &E = colE[j];
                for (int st = 0; st < N; ++st) {
                    bool match = true;
                    for (int p = 0; p < k; ++p) {
                        if (E[st + p] != t[p]) { match = false; break; }
                    }
                    if (match) { ok = true; break; }
                }
            }
            if (ok) ++count;
        }
        return count;
    };

    auto findBestPlacement = [&](const vector<vector<char>>& G, const string& t)->Candidate {
        int k = (int)t.size();
        Candidate best;
        for (int i = 0; i < N; ++i) {
            // horizontal
            for (int j = 0; j < N; ++j) {
                int matches = 0, newAssigns = 0;
                bool valid = true;
                for (int p = 0; p < k; ++p) {
                    int jj = (j + p) % N;
                    char g = G[i][jj];
                    if (g == 0) newAssigns++;
                    else if (g == t[p]) matches++;
                    else { valid = false; break; }
                }
                if (valid) {
                    int score = matches * 100 - newAssigns;
                    if (score > best.score || (score == best.score && rng.nextInt(2))) {
                        best.ok = true;
                        best.horiz = true;
                        best.i = i; best.j = j;
                        best.matches = matches;
                        best.newAssigns = newAssigns;
                        best.score = score;
                    }
                }
            }
            // vertical
            for (int j = 0; j < N; ++j) {
                int matches = 0, newAssigns = 0;
                bool valid = true;
                for (int p = 0; p < k; ++p) {
                    int ii = (i + p) % N;
                    char g = G[ii][j];
                    if (g == 0) newAssigns++;
                    else if (g == t[p]) matches++;
                    else { valid = false; break; }
                }
                if (valid) {
                    int score = matches * 100 - newAssigns;
                    if (score > best.score || (score == best.score && rng.nextInt(2))) {
                        best.ok = true;
                        best.horiz = false;
                        best.i = i; best.j = j;
                        best.matches = matches;
                        best.newAssigns = newAssigns;
                        best.score = score;
                    }
                }
            }
        }
        return best;
    };

    vector<vector<char>> bestGrid(N, vector<char>(N, 'A'));
    int bestC = -1;

    // Prepare indices grouped by length descending; shuffle within each length group
    vector<vector<int>> byLen(13);
    for (int i = 0; i < M; ++i) byLen[L[i]].push_back(i);

    int attempts = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - startTime).count();
        if (elapsed > TIME_LIMIT) break;
        attempts++;

        vector<vector<char>> G(N, vector<char>(N, 0));

        // Create order: lengths from 12 down to 2; shuffle within equal lengths
        vector<int> order;
        order.reserve(M);
        for (int len = 12; len >= 2; --len) {
            auto &v = byLen[len];
            if (!v.empty()) {
                // shuffle
                for (int i = (int)v.size() - 1; i > 0; --i) {
                    int j = rng.nextInt(i + 1);
                    swap(v[i], v[j]);
                }
                for (int idx : v) order.push_back(idx);
            }
        }

        // Place greedily
        for (int idx : order) {
            const string &t = S[idx];
            Candidate cand = findBestPlacement(G, t);
            if (!cand.ok) continue;
            int k = (int)t.size();
            if (cand.horiz) {
                int i = cand.i, j = cand.j;
                for (int p = 0; p < k; ++p) {
                    int jj = (j + p) % N;
                    if (G[i][jj] == 0) G[i][jj] = t[p];
                }
            } else {
                int i = cand.i, j = cand.j;
                for (int p = 0; p < k; ++p) {
                    int ii = (i + p) % N;
                    if (G[ii][j] == 0) G[ii][j] = t[p];
                }
            }
        }

        // Fill remaining with random letters
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (G[i][j] == 0) {
                    G[i][j] = char('A' + rng.nextInt(8));
                }
            }
        }

        int c = countMatches(G);
        if (c > bestC) {
            bestC = c;
            bestGrid = G;
        }
    }

    // Output best grid
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) cout << bestGrid[i][j];
        cout << '\n';
    }

    return 0;
}