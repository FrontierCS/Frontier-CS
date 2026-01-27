#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static inline int gc() {
        static const int BUFSIZE = 1 << 20;
        static char buf[BUFSIZE];
        static int idx = 0, size = 0;
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return EOF;
        }
        return buf[idx++];
    }
    template <typename T>
    static inline bool readInt(T &out) {
        int c, s = 1;
        T x = 0;
        c = gc();
        if (c == EOF) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = gc();
            if (c == EOF) return false;
        }
        if (c == '-') { s = -1; c = gc(); }
        for (; c >= '0' && c <= '9'; c = gc())
            x = x * 10 + (c - '0');
        out = x * s;
        return true;
    }
};

struct Node {
    int id;
    int g;
    long long c;
};

struct Cmp {
    bool operator()(const Node &a, const Node &b) const {
        // min-heap by ratio c/g
        __int128 lhs = (__int128)a.c * b.g;
        __int128 rhs = (__int128)b.c * a.g;
        if (lhs != rhs) return lhs > rhs; // a has higher ratio -> lower priority (return true)
        if (a.c != b.c) return a.c > b.c;
        if (a.g != b.g) return a.g < b.g; // prefer larger gain
        return a.id > b.id;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!FastScanner::readInt(n)) return 0;
    FastScanner::readInt(m);

    vector<long long> cost(m + 1);
    for (int i = 1; i <= m; ++i) {
        long long x; FastScanner::readInt(x);
        cost[i] = x;
    }

    vector<vector<int>> elemSets(n + 1);
    vector<vector<int>> sets(m + 1);

    for (int i = 1; i <= n; ++i) {
        int k; FastScanner::readInt(k);
        elemSets[i].reserve(k);
        for (int j = 0; j < k; ++j) {
            int a; FastScanner::readInt(a);
            if (a >= 1 && a <= m) {
                elemSets[i].push_back(a);
                sets[a].push_back(i);
            }
        }
    }

    // Deduplicate element->sets and set->elements
    for (int i = 1; i <= n; ++i) {
        auto &v = elemSets[i];
        sort(v.begin(), v.end());
        v.erase(unique(v.begin(), v.end()), v.end());
    }
    for (int s = 1; s <= m; ++s) {
        auto &v = sets[s];
        sort(v.begin(), v.end());
        v.erase(unique(v.begin(), v.end()), v.end());
    }

    vector<int> gain(m + 1, 0);
    for (int s = 1; s <= m; ++s) gain[s] = (int)sets[s].size();

    vector<char> covered(n + 1, 0);
    vector<int> coverCount(n + 1, 0);
    vector<char> chosen(m + 1, 0);

    priority_queue<Node, vector<Node>, Cmp> pq;
    for (int s = 1; s <= m; ++s) {
        if (gain[s] > 0) pq.push(Node{s, gain[s], cost[s]});
    }

    int uncovered = n;
    vector<int> solution;
    solution.reserve(m);

    // Greedy selection
    while (uncovered > 0 && !pq.empty()) {
        Node nd = pq.top(); pq.pop();
        int id = nd.id;
        if (chosen[id] || gain[id] != nd.g || gain[id] <= 0) continue;

        // choose this set
        chosen[id] = 1;
        solution.push_back(id);
        // mark gain to negative to skip future updates for this chosen set
        gain[id] = -1;

        for (int u : sets[id]) {
            if (!covered[u]) {
                covered[u] = 1;
                ++coverCount[u];
                --uncovered;
                // Decrease gain for all sets containing u
                for (int t : elemSets[u]) {
                    if (t >= 1 && t <= m && gain[t] > 0) {
                        --gain[t];
                        if (gain[t] > 0) pq.push(Node{t, gain[t], cost[t]});
                    }
                }
            } else {
                ++coverCount[u];
            }
        }
    }

    // Fallback (attempt to cover any remaining uncovered elements, if possible)
    if (uncovered > 0) {
        for (int i = 1; i <= n && uncovered > 0; ++i) {
            if (!covered[i]) {
                if (!elemSets[i].empty()) {
                    int t = elemSets[i][0];
                    if (!chosen[t]) {
                        chosen[t] = 1;
                        solution.push_back(t);
                        for (int u : sets[t]) {
                            if (!covered[u]) {
                                covered[u] = 1;
                                --uncovered;
                            }
                            ++coverCount[u];
                        }
                    }
                }
            }
        }
    }

    // Redundancy removal: try to remove sets whose elements remain covered
    if (!solution.empty()) {
        vector<int> order = solution;
        sort(order.begin(), order.end(), [&](int a, int b){
            if (cost[a] != cost[b]) return cost[a] > cost[b]; // remove expensive first
            return a < b;
        });
        for (int s : order) {
            if (!chosen[s]) continue;
            bool canRemove = true;
            for (int u : sets[s]) {
                if (coverCount[u] <= 1) { canRemove = false; break; }
            }
            if (canRemove) {
                chosen[s] = 0;
                for (int u : sets[s]) --coverCount[u];
            }
        }
    }

    // Build final solution list
    vector<int> finalSol;
    finalSol.reserve(solution.size());
    for (int s : solution) if (chosen[s]) finalSol.push_back(s);

    // Output
    printf("%d\n", (int)finalSol.size());
    if (!finalSol.empty()) {
        for (size_t i = 0; i < finalSol.size(); ++i) {
            if (i) printf(" ");
            printf("%d", finalSol[i]);
        }
    }
    printf("\n");
    return 0;
}