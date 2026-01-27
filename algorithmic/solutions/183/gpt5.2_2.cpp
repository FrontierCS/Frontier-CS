#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr int BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = read();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = read();
        }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = read();
        }
        out = neg ? -val : val;
        return true;
    }
};

static inline long long nowMicros() {
    return chrono::duration_cast<chrono::microseconds>(
               chrono::steady_clock::now().time_since_epoch())
        .count();
}

int main() {
    FastScanner fs;
    int N, M;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);

    vector<vector<int>> adj(N);
    adj.reserve(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<int> deg(N, 0);
    for (int i = 0; i < N; i++) {
        auto &a = adj[i];
        sort(a.begin(), a.end());
        a.erase(unique(a.begin(), a.end()), a.end());
        deg[i] = (int)a.size();
    }

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    const long long startMicros = nowMicros();
    const long long timeLimitMicros = 1950000; // ~1.95s
    auto timeOk = [&]() -> bool {
        return nowMicros() - startMicros < timeLimitMicros;
    };

    auto constructMIS = [&](int type) -> vector<char> {
        vector<int> ord(N);
        iota(ord.begin(), ord.end(), 0);

        if (type == 0) { // increasing degree, random tie
            shuffle(ord.begin(), ord.end(), rng);
            stable_sort(ord.begin(), ord.end(), [&](int a, int b) {
                return deg[a] < deg[b];
            });
        } else if (type == 1) { // random
            shuffle(ord.begin(), ord.end(), rng);
        } else { // decreasing degree, random tie
            shuffle(ord.begin(), ord.end(), rng);
            stable_sort(ord.begin(), ord.end(), [&](int a, int b) {
                return deg[a] > deg[b];
            });
        }

        vector<char> chosen(N, 0), blocked(N, 0);
        for (int v : ord) {
            if (!blocked[v]) {
                chosen[v] = 1;
                blocked[v] = 1;
                for (int u : adj[v]) blocked[u] = 1;
            }
        }
        return chosen;
    };

    vector<char> bestChosen;
    int bestCount = -1;

    auto improve = [&](vector<char> &chosen) -> int {
        vector<int> cn(N, 0), uniq(N, -1); // uniq valid only when cn==1
        int chosenCount = 0;
        for (int i = 0; i < N; i++) if (chosen[i]) chosenCount++;

        for (int u = 0; u < N; u++) if (chosen[u]) {
            for (int v : adj[u]) {
                int before = cn[v]++;
                if (before == 0) uniq[v] = u;
                else uniq[v] = -1;
            }
        }

        vector<int> mark(N, 0);
        int stamp = 1;

        auto recomputeUniq = [&](int v) {
            int rem = -1;
            for (int w : adj[v]) {
                if (chosen[w]) { rem = w; break; }
            }
            uniq[v] = rem;
        };

        auto addVertex = [&](int x) {
            // requires !chosen[x] && cn[x]==0
            chosen[x] = 1;
            chosenCount++;
            for (int v : adj[x]) {
                int before = cn[v]++;
                if (before == 0) uniq[v] = x;
                else uniq[v] = -1;
            }
        };

        auto removeVertex = [&](int x) {
            chosen[x] = 0;
            chosenCount--;
            for (int v : adj[x]) {
                int after = --cn[v];
                if (after == 0) {
                    uniq[v] = -1;
                } else if (after == 1) {
                    recomputeUniq(v);
                } else {
                    uniq[v] = -1;
                }
            }
        };

        auto tryImproveForU = [&](int u) -> bool {
            vector<int> L;
            L.reserve(adj[u].size());
            for (int v : adj[u]) {
                if (!chosen[v] && cn[v] == 1 && uniq[v] == u) L.push_back(v);
            }
            if ((int)L.size() < 2) return false;

            shuffle(L.begin(), L.end(), rng);
            stable_sort(L.begin(), L.end(), [&](int a, int b) {
                return deg[a] < deg[b];
            });

            int a = -1, b = -1;
            int maxA = min<int>((int)L.size(), 10);
            for (int i = 0; i < maxA && b == -1; i++) {
                int x = L[i];
                stamp++;
                if (stamp == INT_MAX) {
                    fill(mark.begin(), mark.end(), 0);
                    stamp = 1;
                }
                mark[x] = stamp;
                for (int w : adj[x]) mark[w] = stamp;

                for (int j = i + 1; j < (int)L.size(); j++) {
                    int y = L[j];
                    if (mark[y] != stamp) {
                        a = x; b = y;
                        break;
                    }
                }
            }
            if (b == -1) return false;

            removeVertex(u);
            // after removing u, a and b should become free (cn==0)
            if (!chosen[a] && cn[a] == 0) addVertex(a);
            else {
                // rollback (shouldn't happen)
                addVertex(u);
                return false;
            }
            if (!chosen[b] && cn[b] == 0) addVertex(b);
            else {
                // rollback (shouldn't happen)
                removeVertex(a);
                addVertex(u);
                return false;
            }

            // Greedily add more from L that became free, to maximize locally
            for (int v : L) {
                if (!chosen[v] && cn[v] == 0) addVertex(v);
            }
            return true;
        };

        for (int pass = 0; pass < 4 && timeOk(); pass++) {
            bool any = false;

            for (int u = 0; u < N && timeOk(); u++) {
                if (!chosen[u]) continue;
                if (tryImproveForU(u)) any = true;
            }

            // Ensure maximality (cheap pass)
            for (int v = 0; v < N && timeOk(); v++) {
                if (!chosen[v] && cn[v] == 0) {
                    addVertex(v);
                    any = true;
                }
            }

            if (!any) break;
        }

        return chosenCount;
    };

    int iters = 0;
    while (timeOk()) {
        int type = iters % 3;
        vector<char> chosen = constructMIS(type);
        int cnt = improve(chosen);
        if (cnt > bestCount) {
            bestCount = cnt;
            bestChosen = move(chosen);
        }
        iters++;
        if (iters >= 30 && bestCount >= N) break;
    }

    if (bestChosen.empty()) bestChosen.assign(N, 0);

    string out;
    out.reserve((size_t)N * 2);
    for (int i = 0; i < N; i++) {
        out.push_back(bestChosen[i] ? '1' : '0');
        out.push_back('\n');
    }
    fwrite(out.c_str(), 1, out.size(), stdout);
    return 0;
}