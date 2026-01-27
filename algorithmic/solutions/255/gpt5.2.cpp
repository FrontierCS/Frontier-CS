#include <bits/stdc++.h>
using namespace std;

struct Node {
    vector<int> idx;
    int l = -1, r = -1;
};

static int ask(const vector<int>& L, const vector<int>& R) {
    cout << "? " << (int)L.size() << " " << (int)R.size() << "\n";
    for (int i = 0; i < (int)L.size(); i++) {
        if (i) cout << ' ';
        cout << L[i];
    }
    cout << "\n";
    for (int i = 0; i < (int)R.size(); i++) {
        if (i) cout << ' ';
        cout << R[i];
    }
    cout << "\n";
    cout.flush();

    int F;
    if (!(cin >> F)) exit(0);
    return F;
}

static int addNode(vector<Node>& nodes, int a, int b) {
    Node p;
    p.l = a; p.r = b;
    p.idx.reserve(nodes[a].idx.size() + nodes[b].idx.size());
    p.idx.insert(p.idx.end(), nodes[a].idx.begin(), nodes[a].idx.end());
    p.idx.insert(p.idx.end(), nodes[b].idx.begin(), nodes[b].idx.end());
    nodes.push_back(std::move(p));
    return (int)nodes.size() - 1;
}

static void solveCase(int n) {
    vector<Node> nodes;
    nodes.reserve(2 * n + 5);
    vector<int> cur;
    cur.reserve(n);

    for (int i = 1; i <= n; i++) {
        Node nd;
        nd.idx = {i};
        nodes.push_back(std::move(nd));
        cur.push_back(i - 1);
    }

    int A = -1, B = -1;

    while (true) {
        vector<int> nxt;
        nxt.reserve((cur.size() + 1) / 2);
        bool found = false;

        for (int i = 0; i < (int)cur.size(); i += 2) {
            if (i + 1 == (int)cur.size()) {
                nxt.push_back(cur[i]);
                continue;
            }
            int u = cur[i], v = cur[i + 1];
            int F = ask(nodes[u].idx, nodes[v].idx);
            if (F != 0) {
                A = u; B = v;
                found = true;
                break;
            } else {
                int p = addNode(nodes, u, v);
                nxt.push_back(p);
            }
        }

        if (found) break;
        cur.swap(nxt);
    }

    // Descend inside A to find a non-demagnetized singleton using B as reference.
    int x = A;
    while (nodes[x].l != -1) {
        int lc = nodes[x].l, rc = nodes[x].r;
        int F = ask(nodes[lc].idx, nodes[B].idx);
        if (F != 0) x = lc;
        else x = rc;
    }
    int ref = nodes[x].idx[0]; // guaranteed non-demagnetized

    vector<int> demag;
    demag.reserve(n);

    for (int i = 1; i <= n; i++) {
        if (i == ref) continue;
        int F = ask(vector<int>{ref}, vector<int>{i});
        if (F == 0) demag.push_back(i);
    }

    cout << "! " << demag.size();
    for (int v : demag) cout << ' ' << v;
    cout << "\n";
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        solveCase(n);
    }
    return 0;
}