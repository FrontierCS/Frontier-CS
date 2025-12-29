#include <bits/stdc++.h>
using namespace std;

struct RNG {
    uint64_t s;
    explicit RNG(uint64_t seed) : s(seed) {}
    uint64_t nextU64() {
        uint64_t z = (s += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    int nextInt(int bound) {
        return (int)(nextU64() % (uint64_t)bound);
    }
    template <class T>
    void shuffleVec(vector<T>& v) {
        for (int i = (int)v.size() - 1; i > 0; --i) {
            int j = nextInt(i + 1);
            swap(v[i], v[j]);
        }
    }
};

static inline long long C2(long long x) { return x * (x - 1) / 2; }

static void buildPairBased(int N, int M, vector<pair<int,int>>& edges) {
    edges.clear();
    edges.reserve((size_t)N * (size_t)M);
    long long B = C2(N);
    int t = (int)min<long long>(M, B);
    int col = 0;
    for (int i = 0; i < N && col < t; ++i) {
        for (int j = i + 1; j < N && col < t; ++j) {
            edges.push_back({i, col});
            edges.push_back({j, col});
            ++col;
        }
    }
    for (; col < M; ++col) edges.push_back({0, col});
}

static void buildGreedyCliquePacking(int N, int M, int baseCap, bool dynamicCap, int offset,
                                     uint64_t seed, vector<pair<int,int>>& edges) {
    edges.clear();
    edges.reserve((size_t)N * (size_t)M);

    int L = (N + 63) / 64;
    vector<uint64_t> used((size_t)N * (size_t)L, 0ULL); // used[i*L + w] bitset of row-pairs used with i
    vector<int> deg(N, 0);

    long long B = C2(N);
    long long usedPairs = 0;

    RNG rng(seed);
    vector<int> colOrder(M);
    iota(colOrder.begin(), colOrder.end(), 0);
    rng.shuffleVec(colOrder);

    vector<int> rows(N);
    array<uint64_t, 8> block{}; // L <= 5 (since N <= 316), but keep some headroom
    vector<int> chosen;
    chosen.reserve(min(N, baseCap));

    for (int idx = 0; idx < M; ++idx) {
        int col = colOrder[idx];

        int cap = baseCap;
        if (dynamicCap && N >= 2) {
            long long remCols = (long long)M - idx;
            long long remPairs = B - usedPairs;
            if (remPairs <= 0) {
                cap = 1;
            } else {
                double avg = (double)remPairs / (double)remCols;
                int s = (int)floor((1.0 + sqrt(1.0 + 8.0 * avg)) / 2.0);
                cap = min(cap, min(N, max(1, s + offset)));
            }
        }
        cap = max(1, min(cap, N));

        iota(rows.begin(), rows.end(), 0);
        rng.shuffleVec(rows);
        stable_sort(rows.begin(), rows.end(), [&](int a, int b) {
            return deg[a] < deg[b];
        });

        for (int w = 0; w < L; ++w) block[w] = 0ULL;
        chosen.clear();
        chosen.reserve(cap);

        for (int r : rows) {
            if ((int)chosen.size() >= cap) break;
            bool ok = true;
            size_t base = (size_t)r * (size_t)L;
            for (int w = 0; w < L; ++w) {
                if (used[base + w] & block[w]) { ok = false; break; }
            }
            if (!ok) continue;
            chosen.push_back(r);
            block[r >> 6] |= (1ULL << (r & 63));
        }
        if (chosen.empty()) {
            chosen.push_back(rows[0]);
        }

        int s = (int)chosen.size();
        usedPairs += C2(s);

        for (int i = 0; i < s; ++i) {
            int a = chosen[i];
            for (int j = i + 1; j < s; ++j) {
                int b = chosen[j];
                used[(size_t)a * (size_t)L + (b >> 6)] |= (1ULL << (b & 63));
                used[(size_t)b * (size_t)L + (a >> 6)] |= (1ULL << (a & 63));
                ++deg[a];
                ++deg[b];
            }
        }

        for (int r : chosen) edges.push_back({r, col});
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    bool transpose = false;
    int N = n, M = m;
    if (n > m) {
        transpose = true;
        N = m;
        M = n;
    }

    vector<pair<int,int>> best, cand;

    long long B = C2(N);

    // Always have a valid baseline.
    buildPairBased(N, M, best);

    if (M < B) {
        // Try randomized clique-packings with various caps around the estimated average.
        double avgPairs = (double)B / (double)M;
        int s0 = (int)floor((1.0 + sqrt(1.0 + 8.0 * avgPairs)) / 2.0);
        s0 = max(2, min(N, s0));

        vector<int> caps;
        auto addCap = [&](int x) {
            x = max(1, min(N, x));
            caps.push_back(x);
        };
        addCap(2);
        addCap(s0);
        addCap(s0 + 1);
        addCap(s0 + 2);
        addCap(s0 + 4);
        addCap(N);
        sort(caps.begin(), caps.end());
        caps.erase(unique(caps.begin(), caps.end()), caps.end());

        uint64_t baseSeed = chrono::high_resolution_clock::now().time_since_epoch().count();
        for (int cap : caps) {
            int runs = (cap == N ? 1 : 3);
            for (int r = 0; r < runs; ++r) {
                int offset = (r == 0 ? 1 : (r == 1 ? 2 : 0));
                uint64_t seed = baseSeed
                                ^ (uint64_t)cap * 0x9e3779b97f4a7c15ULL
                                ^ (uint64_t)(r + 1) * 0xbf58476d1ce4e5b9ULL;
                buildGreedyCliquePacking(N, M, cap, true, offset, seed, cand);
                if (cand.size() > best.size()) best.swap(cand);
            }
        }
        // One extra run without dynamic cap.
        {
            int cap = min(N, s0 + 2);
            uint64_t seed = baseSeed ^ 0x94d049bb133111ebULL ^ (uint64_t)cap * 0x632BE59BD9B4E019ULL;
            buildGreedyCliquePacking(N, M, cap, false, 0, seed, cand);
            if (cand.size() > best.size()) best.swap(cand);
        }
    }

    cout << best.size() << "\n";
    for (auto [r, c] : best) {
        int rr, cc;
        if (!transpose) {
            rr = r + 1;
            cc = c + 1;
        } else {
            rr = c + 1;
            cc = r + 1;
        }
        cout << rr << " " << cc << "\n";
    }
    return 0;
}