#include <bits/stdc++.h>
using namespace std;

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    uint64_t nextU64() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
    int nextInt(int bound) { return (int)(nextU64() % (uint64_t)bound); }
};

struct OrientationData {
    vector<uint8_t> dir;        // size M, 0: U->V, 1: V->U
    vector<int> comp;           // size N
    int K = 0;                  // #SCC
    vector<uint64_t> reach;     // size K*B (bitset over vertices)
};

struct Solver {
    int N, M;
    vector<int> U, V;

    int B; // words in bitset over vertices
    uint64_t lastMask;

    // candidate matrix in bitset rows: cand[a] is bitset of possible B for A=a
    vector<uint64_t> candMat;
    long long totalPairs = 0;

    bool listMode = false;
    vector<pair<int,int>> candPairs;

    // scratch for building directed graph
    vector<int> headOut, headIn;
    vector<int> toOut, toIn;
    vector<int> nxtOut, nxtIn;
    vector<int> fromOut;

    // scratch for SCC
    vector<char> vis;
    vector<int> order;

    // condensation scratch
    vector<int> headC, toC, nxtC, indeg, topo, qvec;

    // permutation scratch
    vector<int> perm, pos;

    SplitMix64 rng;

    Solver(int n, int m) : N(n), M(m) {
        U.resize(M); V.resize(M);
        B = (N + 63) / 64;
        int rem = N % 64;
        lastMask = (rem == 0) ? ~0ULL : ((1ULL << rem) - 1ULL);

        headOut.assign(N, -1);
        headIn.assign(N, -1);
        toOut.resize(M);
        toIn.resize(M);
        nxtOut.resize(M);
        nxtIn.resize(M);
        fromOut.resize(M);

        vis.assign(N, 0);
        order.reserve(N);

        toC.resize(M);
        nxtC.resize(M);

        perm.resize(N);
        pos.resize(N);

        uint64_t seed = 0x123456789abcdef0ULL;
        seed ^= (uint64_t)N * 0x9e3779b97f4a7c15ULL;
        seed ^= (uint64_t)M * 0xbf58476d1ce4e5b9ULL;
        rng = SplitMix64(seed);

        initCandidates();
    }

    static inline int popc(uint64_t x) { return __builtin_popcountll(x); }
    static inline int ctz(uint64_t x) { return __builtin_ctzll(x); }

    void initCandidates() {
        candMat.assign((size_t)N * B, ~0ULL);
        for (int a = 0; a < N; a++) {
            candMat[(size_t)a * B + (a >> 6)] &= ~(1ULL << (a & 63));
            candMat[(size_t)a * B + (B - 1)] &= lastMask;
        }
        totalPairs = 1LL * N * (N - 1);
    }

    void genDirRandomEdge(vector<uint8_t>& dir) {
        dir.resize(M);
        for (int i = 0; i < M; i++) dir[i] = (uint8_t)(rng.nextU64() & 1ULL);
    }

    void genDirPermutation(vector<uint8_t>& dir) {
        for (int i = 0; i < N; i++) perm[i] = i;
        for (int i = N - 1; i >= 1; i--) {
            int j = rng.nextInt(i + 1);
            swap(perm[i], perm[j]);
        }
        for (int i = 0; i < N; i++) pos[perm[i]] = i;

        dir.resize(M);
        for (int i = 0; i < M; i++) {
            int a = U[i], b = V[i];
            dir[i] = (pos[a] < pos[b]) ? 0 : 1;
        }
    }

    void buildDirected(const vector<uint8_t>& dir) {
        fill(headOut.begin(), headOut.end(), -1);
        fill(headIn.begin(), headIn.end(), -1);

        for (int i = 0; i < M; i++) {
            int a = (dir[i] == 0) ? U[i] : V[i];
            int b = (dir[i] == 0) ? V[i] : U[i];
            fromOut[i] = a;
            toOut[i] = b;

            nxtOut[i] = headOut[a];
            headOut[a] = i;

            toIn[i] = a;
            nxtIn[i] = headIn[b];
            headIn[b] = i;
        }
    }

    void kosaraju(vector<int>& comp, int& K) {
        fill(vis.begin(), vis.end(), 0);
        order.clear();
        vector<pair<int,int>> st;
        st.reserve(N);

        for (int s = 0; s < N; s++) {
            if (vis[s]) continue;
            vis[s] = 1;
            st.clear();
            st.push_back({s, headOut[s]});
            while (!st.empty()) {
                auto &tp = st.back();
                int v = tp.first;
                int &e = tp.second;
                if (e == -1) {
                    order.push_back(v);
                    st.pop_back();
                    continue;
                }
                int id = e;
                e = nxtOut[id];
                int u = toOut[id];
                if (!vis[u]) {
                    vis[u] = 1;
                    st.push_back({u, headOut[u]});
                }
            }
        }

        comp.assign(N, -1);
        K = 0;
        vector<int> stv;
        stv.reserve(N);

        for (int idx = N - 1; idx >= 0; idx--) {
            int s = order[idx];
            if (comp[s] != -1) continue;
            int cid = K++;
            comp[s] = cid;
            stv.clear();
            stv.push_back(s);
            while (!stv.empty()) {
                int v = stv.back();
                stv.pop_back();
                for (int e = headIn[v]; e != -1; e = nxtIn[e]) {
                    int u = toIn[e];
                    if (comp[u] == -1) {
                        comp[u] = cid;
                        stv.push_back(u);
                    }
                }
            }
        }
    }

    void computeReach(OrientationData& data) {
        buildDirected(data.dir);
        kosaraju(data.comp, data.K);
        int K = data.K;

        headC.assign(K, -1);
        indeg.assign(K, 0);
        int eC = 0;
        for (int i = 0; i < M; i++) {
            int ca = data.comp[fromOut[i]];
            int cb = data.comp[toOut[i]];
            if (ca == cb) continue;
            toC[eC] = cb;
            nxtC[eC] = headC[ca];
            headC[ca] = eC;
            indeg[cb]++;
            eC++;
        }

        topo.clear();
        topo.reserve(K);
        qvec.clear();
        qvec.reserve(K);
        for (int c = 0; c < K; c++) if (indeg[c] == 0) qvec.push_back(c);
        size_t qh = 0;
        while (qh < qvec.size()) {
            int c = qvec[qh++];
            topo.push_back(c);
            for (int e = headC[c]; e != -1; e = nxtC[e]) {
                int d = toC[e];
                if (--indeg[d] == 0) qvec.push_back(d);
            }
        }

        data.reach.assign((size_t)K * B, 0ULL);
        for (int v = 0; v < N; v++) {
            int c = data.comp[v];
            data.reach[(size_t)c * B + (v >> 6)] |= (1ULL << (v & 63));
        }

        for (int ti = K - 1; ti >= 0; ti--) {
            int c = topo[ti];
            uint64_t* dst = data.reach.data() + (size_t)c * B;
            for (int e = headC[c]; e != -1; e = nxtC[e]) {
                int d = toC[e];
                const uint64_t* src = data.reach.data() + (size_t)d * B;
                for (int w = 0; w < B; w++) dst[w] |= src[w];
            }
        }

        // ensure last word masked (not strictly needed since we only set valid bits)
        for (int c = 0; c < K; c++) data.reach[(size_t)c * B + (B - 1)] &= lastMask;
    }

    inline bool canReach(const OrientationData& data, int a, int b) const {
        int c = data.comp[a];
        return (data.reach[(size_t)c * B + (b >> 6)] >> (b & 63)) & 1ULL;
    }

    long long countOnes(const OrientationData& data) {
        if (listMode) {
            long long cnt = 0;
            for (auto [a, b] : candPairs) cnt += canReach(data, a, b);
            return cnt;
        } else {
            long long cnt = 0;
            for (int a = 0; a < N; a++) {
                int c = data.comp[a];
                const uint64_t* r = data.reach.data() + (size_t)c * B;
                const uint64_t* row = candMat.data() + (size_t)a * B;
                for (int w = 0; w < B; w++) cnt += popc(row[w] & r[w]);
            }
            return cnt;
        }
    }

    long long updateCandidates(const OrientationData& data, int ans) {
        if (listMode) {
            vector<pair<int,int>> next;
            next.reserve(candPairs.size());
            if (ans == 1) {
                for (auto [a, b] : candPairs) if (canReach(data, a, b)) next.push_back({a, b});
            } else {
                for (auto [a, b] : candPairs) if (!canReach(data, a, b)) next.push_back({a, b});
            }
            candPairs.swap(next);
            return (long long)candPairs.size();
        } else {
            long long newTotal = 0;
            for (int a = 0; a < N; a++) {
                int c = data.comp[a];
                const uint64_t* r = data.reach.data() + (size_t)c * B;
                uint64_t* row = candMat.data() + (size_t)a * B;
                if (ans == 1) {
                    for (int w = 0; w < B; w++) row[w] &= r[w];
                } else {
                    for (int w = 0; w < B; w++) row[w] &= ~r[w];
                }
                row[B - 1] &= lastMask;
                for (int w = 0; w < B; w++) newTotal += popc(row[w]);
            }
            return newTotal;
        }
    }

    void maybeConvertToList() {
        static const long long LIST_THRESHOLD = 200000;
        if (listMode) return;
        if (totalPairs > LIST_THRESHOLD) return;

        candPairs.clear();
        candPairs.reserve((size_t)max(1LL, totalPairs));
        for (int a = 0; a < N; a++) {
            const uint64_t* row = candMat.data() + (size_t)a * B;
            for (int w = 0; w < B; w++) {
                uint64_t x = row[w];
                while (x) {
                    int t = ctz(x);
                    int b = (w << 6) + t;
                    if (b < N) candPairs.push_back({a, b});
                    x &= x - 1;
                }
            }
        }
        listMode = true;
        vector<uint64_t>().swap(candMat);
        totalPairs = (long long)candPairs.size();
    }

    pair<int,int> getAnyCandidateFromMatrix() {
        for (int a = 0; a < N; a++) {
            const uint64_t* row = candMat.data() + (size_t)a * B;
            for (int w = 0; w < B; w++) {
                uint64_t x = row[w];
                if (!x) continue;
                int t = ctz(x);
                int b = (w << 6) + t;
                if (b < N) return {a, b};
            }
        }
        return {0, 1};
    }

    void outputQuery(const vector<uint8_t>& dir) {
        string out;
        out.reserve((size_t)2 * M + 4);
        out.push_back('0');
        for (int i = 0; i < M; i++) {
            out.push_back(' ');
            out.push_back(char('0' + dir[i]));
        }
        out.push_back('\n');
        cout << out;
        cout.flush();
    }

    int readAnswer() {
        int x;
        if (!(cin >> x)) exit(0);
        return x;
    }

    [[noreturn]] void outputFinal(int A, int B) {
        cout << "1 " << A << " " << B << "\n";
        cout.flush();
        exit(0);
    }

    void solveInteractive() {
        const int MAXQ = 600;
        int q = 0;

        while (totalPairs > 1 && q < MAXQ) {
            maybeConvertToList();

            OrientationData best, tmp;
            long long bestCnt1 = -1;
            long long bestScore = -1;

            auto consider = [&](OrientationData& cand) {
                computeReach(cand);
                long long cnt1 = countOnes(cand);
                long long cnt0 = totalPairs - cnt1;
                long long score = min(cnt1, cnt0);
                if (score > bestScore) {
                    bestScore = score;
                    bestCnt1 = cnt1;
                    best = std::move(cand);
                }
            };

            // Attempt 1: random edge directions
            tmp = OrientationData();
            genDirRandomEdge(tmp.dir);
            consider(tmp);

            // Attempt 2: only if first split is poor
            if (!listMode) {
                if (bestScore < max(1LL, totalPairs / 10)) {
                    tmp = OrientationData();
                    genDirPermutation(tmp.dir);
                    consider(tmp);
                }
            } else {
                tmp = OrientationData();
                genDirPermutation(tmp.dir);
                consider(tmp);
            }

            // Ask using best orientation
            outputQuery(best.dir);
            int ans = readAnswer();
            q++;

            totalPairs = updateCandidates(best, ans);

            if (totalPairs <= 1) break;
        }

        if (totalPairs == 1) {
            int A, B;
            if (listMode) {
                A = candPairs[0].first;
                B = candPairs[0].second;
            } else {
                auto pr = getAnyCandidateFromMatrix();
                A = pr.first;
                B = pr.second;
            }
            outputFinal(A, B);
        } else {
            // Fallback (should not happen): output any remaining candidate
            int A, B;
            if (listMode && !candPairs.empty()) {
                A = candPairs[0].first;
                B = candPairs[0].second;
            } else if (!listMode) {
                auto pr = getAnyCandidateFromMatrix();
                A = pr.first;
                B = pr.second;
            } else {
                A = 0; B = 1;
            }
            outputFinal(A, B);
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;
    Solver solver(N, M);
    for (int i = 0; i < M; i++) {
        cin >> solver.U[i] >> solver.V[i];
    }
    solver.solveInteractive();
    return 0;
}