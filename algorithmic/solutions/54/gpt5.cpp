#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    auto ask = [&](int u, int v) -> int {
        cout << "? " << u << " " << v << "\n";
        cout.flush();
        int d;
        if (!(cin >> d)) exit(0);
        return d;
    };

    // Step 1: find one diameter endpoint (b) by querying from node 1
    int a1 = 1;
    vector<int> d1(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        if (v == a1) continue;
        d1[v] = ask(a1, v);
    }
    int b = a1;
    for (int v = 1; v <= n; ++v) if (d1[v] > d1[b]) b = v;

    // Step 2: distances from b to all to find the other endpoint c
    vector<int> db(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        if (v == b) continue;
        db[v] = ask(b, v);
    }
    int c = b;
    for (int v = 1; v <= n; ++v) if (db[v] > db[c]) c = v;
    int D = db[c];

    // Step 3: distances from c to all
    vector<int> dc(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        if (v == c) continue;
        dc[v] = ask(c, v);
    }

    // Identify nodes on the diameter path and attachment counts per position
    vector<int> pathNode(D + 1, -1);
    vector<int> attachCount(D + 1, 0);

    for (int v = 1; v <= n; ++v) {
        if (db[v] + dc[v] == D) {
            // v is on the path at position k = db[v]
            int k = db[v];
            if (k >= 0 && k <= D) pathNode[k] = v;
        } else {
            // off-path node, compute its projection index
            int val = db[v] + D - dc[v];
            // val should be even in a tree metric
            int s = val / 2;
            if (s < 0) s = 0;
            if (s > D) s = D;
            attachCount[s]++;
        }
    }

    int totAttach = n - (D + 1);

    // Prefix sums of attachments
    vector<int> pref(D + 2, 0); // pref[i] = sum attachCount[0..i-1]
    for (int i = 0; i <= D; ++i) pref[i + 1] = pref[i] + attachCount[i];

    // Choose k minimizing max(left, right)
    int bestK = 0;
    int bestVal = INT_MAX;
    for (int k = 0; k <= D; ++k) {
        int left = pref[k] + k;
        int right = (totAttach - pref[k] - attachCount[k]) + (D - k);
        int cur = max(left, right);
        if (cur < bestVal) {
            bestVal = cur;
            bestK = k;
        }
    }

    int centroid = pathNode[bestK];
    if (centroid <= 0) {
        // Fallback: if something went wrong, default to one endpoint
        centroid = b;
    }

    cout << "! " << centroid << "\n";
    cout.flush();
    return 0;
}