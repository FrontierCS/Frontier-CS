#include <bits/stdc++.h>
using namespace std;

const int MAXN = 600000;

int child[2][MAXN];          // trie children
unsigned char endBit[2][MAXN]; // edge to sink flags for last bit 0/1
int depthArr[MAXN];
vector<int> nodesAtDepth[25];

int newId_[MAXN];            // trie node -> canonical state id

int stChild0[MAXN], stChild1[MAXN];
unsigned char stEnd0[MAXN], stEnd1[MAXN];

int finalChild0[MAXN], finalChild1[MAXN];
unsigned char finalEnd0[MAXN], finalEnd1[MAXN];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long L, R;
    if (!(cin >> L >> R)) return 0;

    int TOT = 1; // root = 1
    depthArr[1] = 0;
    nodesAtDepth[0].push_back(1);
    int maxDepth = 0;

    for (long long x = L; x <= R; ++x) {
        int len = 64 - __builtin_clzll(x); // number of bits
        int node = 1;
        for (int pos = len - 1; pos >= 1; --pos) {
            int b = (x >> pos) & 1;
            int &nxt = child[b][node];
            if (nxt == 0) {
                ++TOT;
                nxt = TOT;
                depthArr[TOT] = depthArr[node] + 1;
                nodesAtDepth[depthArr[TOT]].push_back(TOT);
                if (depthArr[TOT] > maxDepth) maxDepth = depthArr[TOT];
            }
            node = nxt;
        }
        int lastBit = x & 1;
        endBit[lastBit][node] = 1;
    }

    unordered_map<unsigned long long, int> mp;
    mp.reserve(TOT * 2);
    mp.max_load_factor(0.7f);

    int cnt = 0; // number of canonical prefix states

    for (int d = maxDepth; d >= 0; --d) {
        for (int u : nodesAtDepth[d]) {
            int c0 = child[0][u] ? newId_[child[0][u]] : 0;
            int c1 = child[1][u] ? newId_[child[1][u]] : 0;
            unsigned char e0 = endBit[0][u];
            unsigned char e1 = endBit[1][u];

            unsigned long long key =
                ( (unsigned long long)c0 << 22 ) |
                ( (unsigned long long)c1 << 2 ) |
                ( (unsigned long long)e0 << 1 ) |
                (unsigned long long)e1;

            auto it = mp.find(key);
            if (it != mp.end()) {
                newId_[u] = it->second;
            } else {
                ++cnt;
                newId_[u] = cnt;
                mp[key] = cnt;
                stChild0[cnt] = c0;
                stChild1[cnt] = c1;
                stEnd0[cnt] = e0;
                stEnd1[cnt] = e1;
            }
        }
    }

    int startId = newId_[1];
    int sinkOld = cnt + 1; // conceptual, before renumbering
    int n = cnt + 1;       // total nodes after adding sink

    // Renumber so that start node is 1 and sink is n
    vector<int> perm(cnt + 1), invperm(cnt + 1);
    perm[startId] = 1;
    int cur = 2;
    for (int i = 1; i <= cnt; ++i) {
        if (i == startId) continue;
        perm[i] = cur++;
    }
    for (int i = 1; i <= cnt; ++i) {
        invperm[perm[i]] = i;
    }

    // Build final state descriptions
    for (int oldId = 1; oldId <= cnt; ++oldId) {
        int ni = perm[oldId];
        int c0 = stChild0[oldId];
        int c1 = stChild1[oldId];
        finalChild0[ni] = c0 ? perm[c0] : 0;
        finalChild1[ni] = c1 ? perm[c1] : 0;
        finalEnd0[ni] = stEnd0[oldId];
        finalEnd1[ni] = stEnd1[oldId];
    }
    int sink = n; // sink is node n

    // Output graph
    cout << n << '\n';
    for (int i = 1; i <= n; ++i) {
        if (i == sink) {
            cout << 0 << '\n';
            continue;
        }
        vector<pair<int,int>> edges;
        if (finalChild0[i]) edges.push_back({finalChild0[i], 0});
        if (finalEnd0[i]) edges.push_back({sink, 0});
        if (finalChild1[i]) edges.push_back({finalChild1[i], 1});
        if (finalEnd1[i]) edges.push_back({sink, 1});

        cout << edges.size();
        for (auto &e : edges) {
            cout << ' ' << e.first << ' ' << e.second;
        }
        cout << '\n';
    }

    return 0;
}