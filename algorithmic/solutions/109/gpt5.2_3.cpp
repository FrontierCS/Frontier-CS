#include <bits/stdc++.h>
using namespace std;

struct Node {
    int idx;
    uint8_t tried;
};

struct FastOutput {
    string out;
    void reserve(size_t n) { out.reserve(n); }
    inline void pushChar(char c) { out.push_back(c); }
    inline void pushInt(int x) {
        char s[16];
        int n = 0;
        if (x == 0) s[n++] = '0';
        else {
            while (x > 0) { s[n++] = char('0' + (x % 10)); x /= 10; }
        }
        while (n--) out.push_back(s[n]);
    }
    void flush() {
        fwrite(out.data(), 1, out.size(), stdout);
    }
};

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    int r0, c0;
    cin >> r0 >> c0;
    --r0; --c0;

    const int total = N * N;
    const int dr[8] = {-2,-2,-1,-1, 1, 1, 2, 2};
    const int dc[8] = {-1, 1,-2, 2,-2, 2,-1, 1};

    vector<array<int,8>> neigh(total);
    vector<uint8_t> initDeg(total, 0);

    for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
            int idx = r * N + c;
            array<int,8> a;
            a.fill(-1);
            uint8_t cnt = 0;
            for (int d = 0; d < 8; d++) {
                int nr = r + dr[d], nc = c + dc[d];
                if ((unsigned)nr < (unsigned)N && (unsigned)nc < (unsigned)N) {
                    a[d] = nr * N + nc;
                    cnt++;
                }
            }
            neigh[idx] = a;
            initDeg[idx] = cnt;
        }
    }

    int startIdx = r0 * N + c0;

    auto limitFactor = [&](int n) -> uint64_t {
        if (n <= 10) return 500000ULL;
        if (n <= 20) return 200000ULL;
        if (n <= 30) return 80000ULL;
        if (n <= 50) return 20000ULL;
        if (n <= 80) return 5000ULL;
        if (n <= 120) return 1500ULL;
        if (n <= 200) return 200ULL;
        return 8ULL;
    };

    auto maxTries = [&](int n) -> int {
        if (n <= 10) return 200;
        if (n <= 20) return 120;
        if (n <= 50) return 60;
        if (n <= 100) return 20;
        if (n <= 200) return 8;
        return 3;
    };

    uint64_t limit = (uint64_t)total * limitFactor(N);
    int tries = maxTries(N);

    vector<uint8_t> visited(total);
    vector<uint8_t> deg(total);
    vector<Node> st;
    st.reserve(total);

    auto do_visit = [&](int v) {
        visited[v] = 1;
        const auto &nb = neigh[v];
        for (int d = 0; d < 8; d++) {
            int u = nb[d];
            if (u != -1) deg[u]--;
        }
    };

    auto do_unvisit = [&](int v) {
        visited[v] = 0;
        const auto &nb = neigh[v];
        for (int d = 0; d < 8; d++) {
            int u = nb[d];
            if (u != -1) deg[u]++;
        }
    };

    vector<Node> bestSt;

    bool success = false;
    uint64_t baseSeed = chrono::high_resolution_clock::now().time_since_epoch().count();
    for (int attempt = 0; attempt < tries && !success; attempt++) {
        fill(visited.begin(), visited.end(), 0);
        deg = initDeg;
        st.clear();

        uint64_t seed = splitmix64(baseSeed + (uint64_t)attempt * 0x9e3779b97f4a7c15ULL);
        mt19937_64 rng(seed);

        do_visit(startIdx);
        st.push_back({startIdx, 0});

        uint64_t expansions = 0;
        while (!st.empty() && expansions < limit) {
            if ((int)st.size() == total) { success = true; break; }
            expansions++;

            Node &curNode = st.back();
            int cur = curNode.idx;
            uint8_t mask = curNode.tried;

            int remaining = total - (int)st.size();

            int bestScore = 100;
            uint8_t bestDirs[8];
            int bestCnt = 0;

            const auto &nb = neigh[cur];
            for (int d = 0; d < 8; d++) {
                int nxt = nb[d];
                if (nxt == -1) continue;
                if (mask & (1u << d)) continue;
                if (visited[nxt]) continue;

                int sc = (int)deg[nxt];
                if (remaining > 1 && sc == 0) sc = 9;

                if (sc < bestScore) {
                    bestScore = sc;
                    bestCnt = 0;
                }
                if (sc == bestScore) bestDirs[bestCnt++] = (uint8_t)d;
            }

            if (bestCnt == 0) {
                do_unvisit(cur);
                st.pop_back();
                continue;
            }

            int chosenDir = bestDirs[(size_t)(rng() % (uint64_t)bestCnt)];
            curNode.tried = (uint8_t)(curNode.tried | (1u << chosenDir));
            int nxt = nb[chosenDir];

            do_visit(nxt);
            st.push_back({nxt, 0});
        }

        if (success) break;
        if (st.size() > bestSt.size()) bestSt = st;
    }

    const vector<Node> &ans = success ? st : (bestSt.empty() ? st : bestSt);
    int L = (int)ans.size();

    FastOutput fo;
    fo.reserve((size_t)L * 10 + 32);

    fo.pushInt(L);
    if (L > 0) fo.pushChar('\n');

    for (int i = 0; i < L; i++) {
        int idx = ans[i].idx;
        int r = idx / N + 1;
        int c = idx % N + 1;
        fo.pushInt(r);
        fo.pushChar(' ');
        fo.pushInt(c);
        if (i + 1 < L) fo.pushChar('\n');
    }

    fo.flush();
    return 0;
}