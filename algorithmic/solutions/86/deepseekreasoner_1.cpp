#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> parent;
vector<vector<int>> children;
vector<int> rep;

int ask(int a, int b, int c) {
    cout << "0 " << a << " " << b << " " << c << endl;
    int res;
    cin >> res;
    return res;
}

// find which child of u contains x, or -1 if none
int find_child(int u, int x) {
    vector<int>& ch = children[u];
    if (ch.empty()) return -1;
    vector<int> cand(ch.begin(), ch.end());
    while (!cand.empty()) {
        if (cand.size() == 1) {
            int c = cand[0];
            int res = ask(u, rep[c], x);
            if (res == rep[c]) return c;
            else return -1;
        }
        // split into two roughly equal groups
        int m = cand.size() / 2;
        vector<int> A(cand.begin(), cand.begin() + m);
        vector<int> B(cand.begin() + m, cand.end());
        int a = A[0];
        int b = B[0];
        int res = ask(rep[a], rep[b], x);
        if (res == rep[a]) {
            cand = A;
        } else if (res == rep[b]) {
            cand = B;
        } else if (res == u) {
            // x is not in any child of u within cand
            return -1;
        } else {
            // should not happen
            assert(false);
        }
    }
    return -1;
}

void insert(int x, int root) {
    int u = root;
    while (true) {
        int c = find_child(u, x);
        if (c == -1) {
            // attach x as a child of u
            parent[x] = u;
            children[u].push_back(x);
            rep[x] = x;
            break;
        } else {
            u = c;
        }
    }
}

int main() {
    cin >> n;
    parent.assign(n + 1, -1);
    children.resize(n + 1);
    rep.resize(n + 1);

    // random order of insertion
    vector<int> nodes;
    for (int i = 1; i <= n; ++i) nodes.push_back(i);
    random_shuffle(nodes.begin(), nodes.end());

    int root = nodes[0];
    rep[root] = root;

    for (int i = 1; i < n; ++i) {
        insert(nodes[i], root);
    }

    // output the discovered edges
    cout << "1";
    for (int i = 1; i <= n; ++i) {
        if (parent[i] != -1) {
            cout << " " << parent[i] << " " << i;
        }
    }
    cout << endl;

    return 0;
}