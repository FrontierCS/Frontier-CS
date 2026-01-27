#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char readChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = readChar();
        }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = neg ? -val : val;
        return true;
    }
};

static constexpr int MAXN = 1000;
static constexpr int MAXB = (MAXN + 63) / 64;

static inline int popcount_and_words(const array<uint64_t, MAXB> &a, const array<uint64_t, MAXB> &b, int B) {
    int s = 0;
    for (int i = 0; i < B; ++i) s += __builtin_popcountll(a[i] & b[i]);
    return s;
}

static inline bool any_words(const array<uint64_t, MAXB> &x, int B) {
    for (int i = 0; i < B; ++i) if (x[i]) return true;
    return false;
}

static inline bool test_bit(const array<uint64_t, MAXB> &x, int v) {
    return (x[v >> 6] >> (v & 63)) & 1ULL;
}

static inline void clear_bit(array<uint64_t, MAXB> &x, int v) {
    x[v >> 6] &= ~(1ULL << (v & 63));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int N, M;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);

    const int B = (N + 63) / 64;
    const uint64_t lastMask = (N % 64 == 0) ? ~0ULL : ((1ULL << (N % 64)) - 1ULL);

    vector<array<uint64_t, MAXB>> adj(N);
    for (int i = 0; i < N; ++i) adj[i].fill(0);

    for (int i = 0; i < M; ++i) {
        int u, v;
        fs.readInt(u); fs.readInt(v);
        --u; --v;
        if (u == v) continue;
        adj[u][v >> 6] |= 1ULL << (v & 63);
        adj[v][u >> 6] |= 1ULL << (u & 63);
    }

    vector<int> deg(N, 0);
    for (int i = 0; i < N; ++i) {
        int d = 0;
        for (int k = 0; k < B; ++k) d += __builtin_popcountll(adj[i][k]);
        deg[i] = d;
    }

    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    vector<char> bestIn(N, 0);
    int bestSize = 0;

    vector<int> clique;
    clique.reserve(N);
    vector<int> candList;
    candList.reserve(N);
    vector<int> scores;
    scores.reserve(N);

    auto buildClique = [&](int startV, bool randomize) -> vector<int> {
        array<uint64_t, MAXB> cand;
        cand.fill(0);

        // cand = all vertices
        for (int k = 0; k < B; ++k) cand[k] = ~0ULL;
        cand[B - 1] &= lastMask;

        vector<int> C;
        C.reserve(N);

        if (startV >= 0) {
            C.push_back(startV);
            for (int k = 0; k < B; ++k) cand[k] &= adj[startV][k];
            cand[B - 1] &= lastMask;
            clear_bit(cand, startV);
        }

        while (any_words(cand, B)) {
            candList.clear();
            for (int v = 0; v < N; ++v) if (test_bit(cand, v)) candList.push_back(v);
            if (candList.empty()) break;

            scores.assign(candList.size(), 0);
            int maxScore = -1;
            for (size_t i = 0; i < candList.size(); ++i) {
                int v = candList[i];
                int sc = popcount_and_words(adj[v], cand, B);
                scores[i] = sc;
                if (sc > maxScore) maxScore = sc;
            }

            int chosen = -1;
            if (!randomize) {
                int bestV = candList[0], bestSc = scores[0];
                for (size_t i = 1; i < candList.size(); ++i) {
                    int v = candList[i], sc = scores[i];
                    if (sc > bestSc || (sc == bestSc && v < bestV)) {
                        bestSc = sc;
                        bestV = v;
                    }
                }
                chosen = bestV;
            } else {
                int delta = max(1, maxScore / 10);
                int threshold = maxScore - delta;

                int rclCount = 0;
                for (int sc : scores) if (sc >= threshold) ++rclCount;

                int pick = uniform_int_distribution<int>(0, rclCount - 1)(rng);
                for (size_t i = 0; i < candList.size(); ++i) {
                    if (scores[i] >= threshold) {
                        if (pick-- == 0) {
                            chosen = candList[i];
                            break;
                        }
                    }
                }
                if (chosen < 0) chosen = candList[uniform_int_distribution<int>(0, (int)candList.size() - 1)(rng)];
            }

            C.push_back(chosen);
            for (int k = 0; k < B; ++k) cand[k] &= adj[chosen][k];
            cand[B - 1] &= lastMask;
            clear_bit(cand, chosen);
        }
        return C;
    };

    // Initial deterministic attempt
    {
        auto C = buildClique(-1, false);
        if ((int)C.size() > bestSize) {
            bestSize = (int)C.size();
            fill(bestIn.begin(), bestIn.end(), 0);
            for (int v : C) bestIn[v] = 1;
        }
    }
    // A few deterministic starts from high-degree vertices
    for (int i = 0; i < min(N, 20); ++i) {
        auto C = buildClique(order[i], false);
        if ((int)C.size() > bestSize) {
            bestSize = (int)C.size();
            fill(bestIn.begin(), bestIn.end(), 0);
            for (int v : C) bestIn[v] = 1;
        }
    }

    using Clock = chrono::steady_clock;
    auto t0 = Clock::now();
    auto deadline = t0 + chrono::milliseconds(1850);

    int it = 0;
    while (Clock::now() < deadline) {
        int startV = -1;
        if (uniform_int_distribution<int>(0, 1)(rng) == 0) {
            int top = min(N, 200);
            startV = order[uniform_int_distribution<int>(0, top - 1)(rng)];
        }
        bool randomize = true;
        auto C = buildClique(startV, randomize);
        if ((int)C.size() > bestSize) {
            bestSize = (int)C.size();
            fill(bestIn.begin(), bestIn.end(), 0);
            for (int v : C) bestIn[v] = 1;
        }
        ++it;
        if ((it & 15) == 0 && bestSize == N) break;
    }

    for (int i = 0; i < N; ++i) {
        cout << (bestIn[i] ? 1 : 0) << '\n';
    }
    return 0;
}