#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <algorithm>
using namespace std;

int N, R;
vector<int> U, V;
vector<int> parent; // for nodes 1..2N
vector<int> depth; // for slots 0..N-1
vector<int> type; // 0: AND, 1: OR

void forceOutput(int node, int val, string& s) {
    if (node >= N) {
        s[node] = (val ? '1' : '0');
    } else {
        forceOutput(U[node], val, s);
        forceOutput(V[node], val, s);
    }
}

void buildAssignment(int i, int va, int vb, string& s) {
    // initialize all switches to 0
    s.assign(2*N+1, '0');
    // set children of slot i
    forceOutput(U[i], va, s);
    forceOutput(V[i], vb, s);
    // set off-path inputs of ancestors
    int cur = i;
    while (true) {
        int p = parent[cur];
        if (p == -1) break; // reached root (slot 0 has no parent)
        int other = (U[p] == cur) ? V[p] : U[p];
        int nc = (type[p] == 0) ? 1 : 0; // non-controlling value
        forceOutput(other, nc, s);
        cur = p;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> N >> R;
    U.resize(N);
    V.resize(N);
    for (int i = 0; i < N; i++) {
        cin >> U[i] >> V[i];
    }

    // compute parent for nodes 1..2N
    parent.assign(2*N+1, -1);
    for (int i = 0; i < N; i++) {
        parent[U[i]] = i;
        parent[V[i]] = i;
    }

    // compute depth of slots using BFS from slot 0
    depth.assign(N, -1);
    queue<int> q;
    depth[0] = 0;
    q.push(0);
    while (!q.empty()) {
        int i = q.front(); q.pop();
        // process children
        for (int child : {U[i], V[i]}) {
            if (child < N && depth[child] == -1) {
                depth[child] = depth[i] + 1;
                q.push(child);
            }
        }
    }

    // collect slots in increasing depth order
    vector<int> slots_by_depth(N);
    for (int i = 0; i < N; i++) slots_by_depth[i] = i;
    sort(slots_by_depth.begin(), slots_by_depth.end(),
         [&](int a, int b) { return depth[a] < depth[b]; });

    type.assign(N, 0); // initially assume AND
    int queryCount = 0;
    const int QUERY_LIMIT = 5000;

    for (int i : slots_by_depth) {
        if (queryCount >= QUERY_LIMIT) break;

        string s1, s2;
        buildAssignment(i, 0, 0, s1);
        buildAssignment(i, 0, 1, s2);

        cout << "? " << s1 << endl;
        int o1; cin >> o1;
        queryCount++;
        if (queryCount >= QUERY_LIMIT) break;

        cout << "? " << s2 << endl;
        int o2; cin >> o2;
        queryCount++;

        if (o1 != o2) {
            type[i] = 1; // OR
        } else {
            type[i] = 0; // AND
        }
    }

    // construct answer string
    string ans(N, '&');
    for (int i = 0; i < N; i++) {
        if (