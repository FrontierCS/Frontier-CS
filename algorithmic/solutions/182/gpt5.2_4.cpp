#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr int BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char readChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    int nextInt() {
        char c;
        do { c = readChar(); } while (c <= ' ' && c);
        int sgn = 1;
        if (c == '-') { sgn = -1; c = readChar(); }
        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = readChar();
        }
        return x * sgn;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int N = fs.nextInt();
    int M = fs.nextInt();

    vector<int> U(M), V(M);
    vector<int> deg(N + 2, 0);
    for (int i = 0; i < M; i++) {
        int u = fs.nextInt();
        int v = fs.nextInt();
        U[i] = u; V[i] = v;
        deg[u]++; deg[v]++;
    }

    vector<int> offs(N + 2, 0);
    offs[1] = 0;
    for (int i = 1; i <= N; i++) offs[i + 1] = offs[i] + deg[i];

    vector<int> cur = offs;
    vector<int> adj(2LL * M);
    for (int i = 0; i < M; i++) {
        int u = U[i], v = V[i];
        adj[cur[u]++] = v;
        adj[cur[v]++] = u;
    }

    int maxDeg = 0;
    for (int i = 1; i <= N; i++) maxDeg = max(maxDeg, offs[i + 1] - offs[i]);

    vector<int> vertices(N);
    for (int i = 0; i < N; i++) vertices[i] = i + 1;

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto greedyMIS = [&](const vector<int>& order, vector<char>& inI) -> int {
        vector<char> blocked(N + 1, 0);
        inI.assign(N + 1, 0);
        int cnt = 0;
        for (int v : order) {
            if (!blocked[v]) {
                inI[v] = 1;
                cnt++;
                blocked[v] = 1;
                for (int ei = offs[v]; ei < offs[v + 1]; ei++) blocked[adj[ei]] = 1;
            }
        }
        return cnt;
    };

    auto makeMaximalFromSeed = [&](const vector<char>& seed, const vector<int>& order, vector<char>& outI) -> int {
        vector<char> blocked(N + 1, 0);
        outI = seed;
        int cnt = 0;

        for (int v = 1; v <= N; v++) {
            if (!outI[v]) continue;
            if (blocked[v]) { outI[v] = 0; continue; }
            cnt++;
            blocked[v] = 1;
            for (int ei = offs[v]; ei < offs[v + 1]; ei++) blocked[adj[ei]] = 1;
        }

        for (int v : order) {
            if (!blocked[v]) {
                outI[v] = 1;
                cnt++;
                blocked[v] = 1;
                for (int ei = offs[v]; ei < offs[v + 1]; ei++) blocked[adj[ei]] = 1;
            }
        }
        return cnt;
    };

    int bestCnt = -1;
    vector<char> bestInI;

    auto consider = [&](const vector<int>& order) {
        vector<char> inI;
        int cnt = greedyMIS(order, inI);
        if (cnt > bestCnt) {
            bestCnt = cnt;
            bestInI = std::move(inI);
        }
    };

    // Base runs
    {
        vector<int> order = vertices;
        stable_sort(order.begin(), order.end(), [&](int a, int b) {
            int da = offs[a + 1] - offs[a];
            int db = offs[b + 1] - offs[b];
            if (da != db) return da < db;
            return a < b;
        });
        consider(order);
    }
    {
        vector<int> order = vertices;
        shuffle(order.begin(), order.end(), rng);
        stable_sort(order.begin(), order.end(), [&](int a, int b) {
            int da = offs[a + 1] - offs[a];
            int db = offs[b + 1] - offs[b];
            return da < db;
        });
        consider(order);
    }
    for (int t = 0; t < 2; t++) {
        vector<int> order = vertices;
        shuffle(order.begin(), order.end(), rng);
        consider(order);
    }
    for (int t = 0; t < 3; t++) {
        vector<pair<int,int>> keyed;
        keyed.reserve(N);
        int noiseRange = max(1, maxDeg / (t == 0 ? 1 : (t == 1 ? 2 : 4)));
        uniform_int_distribution<int> dist(0, noiseRange);
        for (int v = 1; v <= N; v++) {
            int d = offs[v + 1] - offs[v];
            int key = d + dist(rng);
            keyed.emplace_back(key, v);
        }
        sort(keyed.begin(), keyed.end(), [&](const auto& A, const auto& B) {
            if (A.first != B.first) return A.first < B.first;
            return A.second < B.second;
        });
        vector<int> order(N);
        for (int i = 0; i < N; i++) order[i] = keyed[i].second;
        consider(order);
    }
    {
        vector<int> order = vertices;
        stable_sort(order.begin(), order.end(), [&](int a, int b) {
            int da = offs[a + 1] - offs[a];
            int db = offs[b + 1] - offs[b];
            if (da != db) return da > db;
            return a < b;
        });
        consider(order);
    }

    // Iterated local search on best independent set
    if (bestCnt < 0) {
        bestInI.assign(N + 1, 0);
        bestCnt = 0;
    }

    for (int iter = 0; iter < 12; iter++) {
        vector<char> seed = bestInI;

        vector<int> indList;
        indList.reserve(bestCnt);
        for (int v = 1; v <= N; v++) if (seed[v]) indList.push_back(v);

        int denom = (iter % 3 == 0 ? 10 : (iter % 3 == 1 ? 20 : 50));
        int k = max(1, (int)indList.size() / denom);

        for (int j = 0; j < k && !indList.empty(); j++) {
            int idx = (int)(rng() % indList.size());
            int v = indList[idx];
            seed[v] = 0;
            indList[idx] = indList.back();
            indList.pop_back();
        }

        vector<int> order = vertices;
        shuffle(order.begin(), order.end(), rng);

        vector<char> inI;
        int cnt = makeMaximalFromSeed(seed, order, inI);
        if (cnt > bestCnt) {
            bestCnt = cnt;
            bestInI = std::move(inI);
        }
    }

    // Safety validation
    bool ok = true;
    for (int i = 0; i < M; i++) {
        if (bestInI[U[i]] && bestInI[V[i]]) { ok = false; break; }
    }
    if (!ok) {
        string out;
        out.reserve(2LL * N);
        for (int i = 1; i <= N; i++) {
            out.push_back('1');
            out.push_back('\n');
        }
        cout << out;
        return 0;
    }

    string out;
    out.reserve(2LL * N);
    for (int i = 1; i <= N; i++) {
        out.push_back(bestInI[i] ? '0' : '1');
        out.push_back('\n');
    }
    cout << out;
    return 0;
}