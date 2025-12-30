#include <bits/stdc++.h>
using namespace std;

static int n;
static long long l1_lim, l2_lim;
static long long qcnt = 0, scnt = 0;

static vector<int> idAtPos, posOfId;

static void die() {
    exit(0);
}

static int ask_segments(int l, int r) {
    if (l > r) die();
    cout << "1 " << l << " " << r << "\n";
    cout.flush();
    int x;
    if (!(cin >> x)) die();
    if (x < 0) die();
    ++qcnt;
    return x;
}

static int ask_edges(int l, int r) {
    if (l > r) return 0;
    if (l == r) return 0;
    int seg = ask_segments(l, r);
    int len = r - l + 1;
    return len - seg;
}

static void do_swap_pos(int i, int j) {
    if (i == j) return;
    cout << "2 " << i << " " << j << "\n";
    cout.flush();
    int ok;
    if (!(cin >> ok)) die();
    if (ok != 1) die();
    ++scnt;
    int a = idAtPos[i], b = idAtPos[j];
    swap(idAtPos[i], idAtPos[j]);
    posOfId[a] = j;
    posOfId[b] = i;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> l1_lim >> l2_lim)) return 0;

    if (n == 1) {
        cout << "3 1\n";
        cout.flush();
        return 0;
    }

    idAtPos.assign(n + 1, 0);
    posOfId.assign(n + 1, 0);
    for (int i = 1; i <= n; i++) {
        idAtPos[i] = i;
        posOfId[i] = i;
    }

    vector<int> deg(n + 1, 0);

    // Degree of vertex v in the value-adjacency path:
    // deg(v) = (n-1) - edges(V\{v})
    // For a path, edges(V\{v}) = (n-1-1) if v is endpoint else (n-1-2),
    // which implies deg(v) is 1 or 2. We'll compute via edges.
    for (int v = 1; v <= n; v++) {
        int pv = posOfId[v];
        if (pv != n) do_swap_pos(pv, n);

        int e_remain = ask_edges(1, n - 1); // induced edges among all except v
        deg[v] = (n - 1) - e_remain;

        if (pv != n) do_swap_pos(pv, n);

        if (qcnt > l1_lim || scnt > l2_lim) die();
    }

    vector<int> endpoints;
    endpoints.reserve(2);
    for (int v = 1; v <= n; v++) {
        if (deg[v] == 1) endpoints.push_back(v);
    }
    if (endpoints.empty()) endpoints.push_back(1); // fallback (shouldn't happen)

    int start = endpoints[0];

    // Bring start to position 1
    do_swap_pos(posOfId[start], 1);

    // Build path order into positions [1..n]
    int k = 1;
    while (k < n) {
        int L = k + 1, R = n;
        while (L < R) {
            int mid = (L + R) >> 1;
            int eA = ask_edges(k + 1, mid);
            int eAu = ask_edges(k, mid);
            int d = eAu - eA; // number of neighbors of idAtPos[k] inside positions [k+1..mid]
            if (d >= 1) R = mid;
            else L = mid + 1;

            if (qcnt > l1_lim || scnt > l2_lim) die();
        }
        if (L != k + 1) do_swap_pos(L, k + 1);
        ++k;

        if (qcnt > l1_lim || scnt > l2_lim) die();
    }

    // Now ids are in value-path order along positions 1..n.
    // Output one valid labeling: assign value i to position i.
    cout << "3";
    for (int i = 1; i <= n; i++) cout << " " << i;
    cout << "\n";
    cout.flush();
    return 0;
}