#include <bits/stdc++.h>
using namespace std;

struct XorShift64 {
    uint64_t x;
    XorShift64(uint64_t seed = 88172645463325252ULL) : x(seed) {}
    inline uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline int randint(int l, int r) { return l + (int)(next() % (uint64_t)(r - l + 1)); }
    template <class T>
    inline void shuffle_vec(vector<T>& v) {
        for (int i = (int)v.size() - 1; i > 0; --i) {
            int j = (int)(next() % (uint64_t)(i + 1));
            swap(v[i], v[j]);
        }
    }
};

static inline int count_covered(const vector<int8_t>& grid, const vector<vector<uint8_t>>& strings, int N) {
    int M = (int)strings.size();
    int covered = 0;
    for (int si = 0; si < M; ++si) {
        const auto& s = strings[si];
        int k = (int)s.size();
        bool ok = false;
        // Horizontal
        for (int i = 0; i < N && !ok; ++i) {
            for (int j = 0; j < N && !ok; ++j) {
                bool good = true;
                int col = j;
                for (int p = 0; p < k; ++p) {
                    int c = col + p;
                    if (c >= N) c -= N;
                    int pos = i * N + c;
                    if (grid[pos] != (int8_t)s[p]) { good = false; break; }
                }
                if (good) { ok = true; break; }
            }
        }
        // Vertical
        if (!ok) {
            for (int j = 0; j < N && !ok; ++j) {
                for (int i = 0; i < N && !ok; ++i) {
                    bool good = true;
                    int row = i;
                    for (int p = 0; p < k; ++p) {
                        int r = row + p;
                        if (r >= N) r -= N;
                        int pos = r * N + j;
                        if (grid[pos] != (int8_t)s[p]) { good = false; break; }
                    }
                    if (good) { ok = true; break; }
                }
            }
        }
        if (ok) ++covered;
    }
    return covered;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    vector<string> s_raw(M);
    for (int i = 0; i < M; ++i) cin >> s_raw[i];

    vector<vector<uint8_t>> strings(M);
    vector<int> slen(M);
    vector<int> order(M);
    vector<int> freq(8, 0);
    for (int i = 0; i < M; ++i) {
        strings[i].resize(s_raw[i].size());
        for (int j = 0; j < (int)s_raw[i].size(); ++j) {
            uint8_t c = (uint8_t)(s_raw[i][j] - 'A');
            strings[i][j] = c;
            if (c < 8) freq[c]++;
        }
        slen[i] = (int)strings[i].size();
        order[i] = i;
    }

    XorShift64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    // Sort by length descending, shuffle beforehand for random tie-breaking
    rng.shuffle_vec(order);
    stable_sort(order.begin(), order.end(), [&](int a, int b) {
        return slen[a] > slen[b];
    });

    const double timeLimitSec = 1.9;
    auto start = chrono::high_resolution_clock::now();

    vector<int8_t> bestGrid(N * N, 0);
    int bestC = -1;

    long long totalFreq = 0;
    for (int f : freq) totalFreq += f;
    if (totalFreq == 0) totalFreq = 8;

    int attempts = 0;
    while (true) {
        ++attempts;
        vector<int8_t> grid(N * N, (int8_t)-1);

        // Multi-pass greedy placement
        int passes = 2;
        for (int pass = 0; pass < passes; ++pass) {
            for (int idx = 0; idx < M; ++idx) {
                int si = order[idx];
                const auto& s = strings[si];
                int k = (int)s.size();

                int best_dir = -1, best_a = -1, best_b = -1;
                int best_fill = 1e9;
                int best_match = -1;

                int a0 = rng.randint(0, N - 1);
                int b0 = rng.randint(0, N - 1);
                int dir0 = (rng.next() & 1ULL) ? 0 : 1;

                for (int dshift = 0; dshift < 2; ++dshift) {
                    int dir = (dir0 + dshift) & 1;
                    for (int da = 0; da < N; ++da) {
                        int a = a0 + da; if (a >= N) a -= N;
                        for (int db = 0; db < N; ++db) {
                            int b = b0 + db; if (b >= N) b -= N;
                            int fillNew = 0;
                            int matchCount = 0;
                            bool ok = true;
                            if (dir == 0) { // horizontal: row=a, start=b
                                int row = a;
                                int col = b;
                                for (int p = 0; p < k; ++p) {
                                    int c = col + p; if (c >= N) c -= N;
                                    int pos = row * N + c;
                                    int gv = grid[pos];
                                    int ch = (int)s[p];
                                    if (gv == -1) { ++fillNew; }
                                    else if (gv == ch) { ++matchCount; }
                                    else { ok = false; break; }
                                }
                            } else { // vertical: col=a, start=b
                                int col = a;
                                int row = b;
                                for (int p = 0; p < k; ++p) {
                                    int r = row + p; if (r >= N) r -= N;
                                    int pos = r * N + col;
                                    int gv = grid[pos];
                                    int ch = (int)s[p];
                                    if (gv == -1) { ++fillNew; }
                                    else if (gv == ch) { ++matchCount; }
                                    else { ok = false; break; }
                                }
                            }
                            if (!ok) continue;
                            if (fillNew < best_fill || (fillNew == best_fill && matchCount > best_match)) {
                                best_fill = fillNew;
                                best_match = matchCount;
                                best_dir = dir;
                                best_a = a;
                                best_b = b;
                                if (best_fill == 0) goto found_zero_fill;
                            }
                        }
                    }
                }
            found_zero_fill:
                if (best_dir == -1) continue; // no consistent placement
                if (best_fill == 0) continue;  // already exists; no need to place

                if (best_dir == 0) {
                    int row = best_a, col = best_b;
                    for (int p = 0; p < k; ++p) {
                        int c = col + p; if (c >= N) c -= N;
                        int pos = row * N + c;
                        if (grid[pos] == -1) grid[pos] = (int8_t)s[p];
                    }
                } else {
                    int col = best_a, row = best_b;
                    for (int p = 0; p < k; ++p) {
                        int r = row + p; if (r >= N) r -= N;
                        int pos = r * N + col;
                        if (grid[pos] == -1) grid[pos] = (int8_t)s[p];
                    }
                }
            }
        }

        // Fill remaining cells with random letters using frequency distribution
        for (int pos = 0; pos < N * N; ++pos) {
            if (grid[pos] == -1) {
                uint64_t r = rng.next() % (uint64_t)totalFreq;
                long long cum = 0;
                int ch = 0;
                for (int t = 0; t < 8; ++t) {
                    cum += freq[t];
                    if (r < (uint64_t)cum) { ch = t; break; }
                }
                grid[pos] = (int8_t)ch;
            }
        }

        int cval = count_covered(grid, strings, N);
        if (cval > bestC) {
            bestC = cval;
            bestGrid = grid;
        }

        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > timeLimitSec) break;
    }

    static const char cmap[9] = {'A','B','C','D','E','F','G','H','.'};
    for (int i = 0; i < N; ++i) {
        string line;
        line.resize(N);
        for (int j = 0; j < N; ++j) {
            int v = bestGrid[i * N + j];
            if (v >= 0 && v < 8) line[j] = cmap[v];
            else line[j] = '.';
        }
        cout << line << '\n';
    }
    return 0;
}