#include <bits/stdc++.h>
using namespace std;

// Fast input
struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template <typename T>
    bool nextInt(T &out) {
        char c; T sign = 1; T val = 0;
        c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c == '-') { sign = -1; c = getChar(); }
        for (; c >= '0' && c <= '9'; c = getChar()) val = val * 10 + (c - '0');
        out = val * sign;
        return true;
    }
} In;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!In.nextInt(n)) return 0;
    In.nextInt(m);

    // Read scoring parameters (unused)
    for (int i = 0; i < 10; ++i) {
        int tmp; In.nextInt(tmp);
    }

    vector<vector<int>> outScan(n + 1), inScan(n + 1);
    outScan.shrink_to_fit();
    inScan.shrink_to_fit();

    // Read edges
    for (int i = 0; i < m; ++i) {
        int u, v; In.nextInt(u); In.nextInt(v);
        if (u >= 1 && u <= n && v >= 1 && v <= n && u != v) {
            outScan[u].push_back(v);
            inScan[v].push_back(u);
        }
    }

    // Build sorted out adjacency for membership tests
    vector<vector<int>> outSorted(n + 1);
    for (int u = 1; u <= n; ++u) {
        outSorted[u] = outScan[u];
        sort(outSorted[u].begin(), outSorted[u].end());
        outSorted[u].erase(unique(outSorted[u].begin(), outSorted[u].end()), outSorted[u].end());
    }

    auto hasEdge = [&](int u, int v) -> bool {
        const auto &vec = outSorted[u];
        auto it = lower_bound(vec.begin(), vec.end(), v);
        return (it != vec.end() && *it == v);
    };

    vector<int> degOut(n + 1), degIn(n + 1);
    for (int u = 1; u <= n; ++u) {
        degOut[u] = (int)outScan[u].size();
        degIn[u] = (int)inScan[u].size();
    }

    // Attempt runner
    auto runAttempt = [&](int start, int maxInsertionPasses) -> vector<int> {
        vector<char> used(n + 1, 0);
        vector<int> nxt(n + 1, 0), prv(n + 1, 0);
        vector<int> outIter(n + 1, 0), inIter(n + 1, 0);

        int head = start, tail = start;
        used[start] = 1;

        auto extendEnds = [&]() {
            while (true) {
                bool progressed = false;
                // Extend right (tail)
                while (true) {
                    auto &vec = outScan[tail];
                    int &pos = outIter[tail];
                    while (pos < (int)vec.size() && used[vec[pos]]) pos++;
                    if (pos >= (int)vec.size()) break;
                    int v = vec[pos++];
                    if (used[v]) continue;
                    nxt[tail] = v;
                    prv[v] = tail;
                    nxt[v] = 0;
                    used[v] = 1;
                    tail = v;
                    progressed = true;
                }
                // Extend left (head)
                while (true) {
                    auto &vec = inScan[head];
                    int &pos = inIter[head];
                    while (pos < (int)vec.size() && used[vec[pos]]) pos++;
                    if (pos >= (int)vec.size()) break;
                    int u = vec[pos++];
                    if (used[u]) continue;
                    prv[head] = u;
                    nxt[u] = head;
                    prv[u] = 0;
                    used[u] = 1;
                    head = u;
                    progressed = true;
                }
                if (!progressed) break;
            }
        };

        extendEnds();

        auto insertionPass = [&]() -> bool {
            bool changed = false;
            int u = head;
            while (u != 0) {
                int w = nxt[u];
                if (w == 0) break;
                auto &neighbors = outScan[u];
                for (int id = 0; id < (int)neighbors.size(); ++id) {
                    int v = neighbors[id];
                    if (!used[v] && hasEdge(v, w)) {
                        // insert v between u and w
                        nxt[u] = v;
                        prv[v] = u;
                        nxt[v] = w;
                        prv[w] = v;
                        used[v] = 1;
                        w = v; // new w for further chaining
                        changed = true;
                    }
                }
                u = w; // continue from the last inserted node towards tail
            }
            return changed;
        };

        for (int pass = 0; pass < maxInsertionPasses; ++pass) {
            bool ch = insertionPass();
            if (!ch) break;
            extendEnds();
        }

        // Build result sequence
        vector<int> ans;
        ans.reserve(n);
        for (int u = head; u != 0; u = nxt[u]) ans.push_back(u);
        return ans;
    };

    // Prepare start candidates
    int startMaxDegSum = 1, startMaxOut = 1, startMaxIn = 1;
    for (int u = 2; u <= n; ++u) {
        if (degOut[u] + degIn[u] > degOut[startMaxDegSum] + degIn[startMaxDegSum]) startMaxDegSum = u;
        if (degOut[u] > degOut[startMaxOut]) startMaxOut = u;
        if (degIn[u] > degIn[startMaxIn]) startMaxIn = u;
    }

    vector<int> starts;
    auto push_unique = [&](int v) {
        if (v < 1 || v > n) return;
        for (int x : starts) if (x == v) return;
        starts.push_back(v);
    };
    push_unique(startMaxDegSum);
    push_unique(startMaxOut);
    push_unique(startMaxIn);

    // Random candidates
    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    int randomTrials = 5;
    for (int i = 0; i < randomTrials; ++i) {
        int v = (int)(rng() % n) + 1;
        push_unique(v);
    }

    vector<int> bestPath;
    size_t bestLen = 0;

    // Time budget (rough)
    auto t0 = chrono::high_resolution_clock::now();
    const double timeBudget = 3.8; // seconds

    for (size_t i = 0; i < starts.size(); ++i) {
        auto t1 = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(t1 - t0).count();
        if (elapsed > timeBudget) break;

        int start = starts[i];
        vector<int> cand = runAttempt(start, 2);
        if (cand.size() > bestLen) {
            bestLen = cand.size();
            bestPath.swap(cand);
            if (bestLen == (size_t)n) break;
        }
    }

    if (bestPath.empty()) {
        // Fallback: output at least one vertex
        bestPath.push_back(1);
    }

    cout << bestPath.size() << "\n";
    for (size_t i = 0; i < bestPath.size(); ++i) {
        if (i) cout << ' ';
        cout << bestPath[i];
    }
    cout << "\n";
    return 0;
}