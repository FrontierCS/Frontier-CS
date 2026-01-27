#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 1005;

int n;
vector<vector<int>> childrenTree;
vector<int> parentNode;
vector<bool> inA;
vector<pair<int,int>> edges;
int rootNode = 1;

unordered_map<long long, int> cacheAns;

long long keyTrip(int v, int a, int b) {
    if (a > b) swap(a, b);
    // use 10 bits per component (since n <= 1000 < 1024)
    return ( (long long)v << 20 ) | ( (long long)a << 10 ) | (long long)b;
}

int queryPathContains(int v, int a, int b) {
    if (a > b) swap(a, b);
    long long key = keyTrip(v, a, b);
    auto it = cacheAns.find(key);
    if (it != cacheAns.end()) return it->second;

    cout << "? 2 " << v << " " << a << " " << b << endl << flush;
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    cacheAns[key] = ans;
    return ans;
}

int findAttachPoint(int x) {
    int c = rootNode;
    while (true) {
        bool moved = false;
        for (int u : childrenTree[c]) {
            if (queryPathContains(u, x, rootNode) == 1) {
                c = u;
                moved = true;
                break;
            }
        }
        if (!moved) return c;
    }
}

int findIntermediate(int x, int y) {
    for (int i = 1; i <= n; i++) {
        if (i == x) continue;
        if (inA[i]) continue;
        if (queryPathContains(i, x, y) == 1) return i;
    }
    return -1;
}

void addEdgeToA(int u, int v) {
    // attach u under v (v is in A)
    parentNode[u] = v;
    childrenTree[v].push_back(u);
    inA[u] = true;
    edges.emplace_back(u, v);
}

void insertNode(int x);

void ensureInserted(int x) {
    if (!inA[x]) insertNode(x);
}

void insertNode(int x) {
    if (inA[x]) return;
    int y = findAttachPoint(x);
    int z = findIntermediate(x, y);
    if (z == -1) {
        addEdgeToA(x, y);
        return;
    } else {
        ensureInserted(z);
        // after inserting z, try x again
        insertNode(x);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    childrenTree.assign(n + 1, {});
    parentNode.assign(n + 1, -1);
    inA.assign(n + 1, false);
    edges.clear();

    // Initialize with root
    inA[rootNode] = true;
    parentNode[rootNode] = 0;

    for (int i = 1; i <= n; i++) {
        if (!inA[i]) insertNode(i);
    }

    cout << "!" << endl;
    for (auto &e : edges) {
        cout << e.first << " " << e.second << endl;
    }
    cout.flush();
    return 0;
}