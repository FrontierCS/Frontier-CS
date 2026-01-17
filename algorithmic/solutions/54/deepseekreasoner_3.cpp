#include <bits/stdc++.h>
using namespace std;

int query(int u, int v) {
    cout << "? " << u << " " << v << endl;
    cout.flush();
    int d;
    cin >> d;
    return d;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    // Step 1: find one endpoint of a diameter
    vector<int> d1(n + 1);
    d1[1] = 0;
    for (int i = 2; i <= n; ++i) {
        d1[i] = query(1, i);
    }
    int A = 1;
    int maxd = 0;
    for (int i = 2; i <= n; ++i) {
        if (d1[i] > maxd) {
            maxd = d1[i];
            A = i;
        }
    }

    // Step 2: find the other endpoint and distances from A
    vector<int> dA(n + 1);
    dA[A] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i != A) dA[i] = query(A, i);
    }
    int B = A;
    maxd = 0;
    for (int i = 1; i <= n; ++i) {
        if (i != A && dA[i] > maxd) {
            maxd = dA[i];
            B = i;
        }
    }
    int dAB = dA[B];

    // Step 3: distances from B
    vector<int> dB(n + 1);
    dB[B] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i != B) dB[i] = query(B, i);
    }

    // Step 4: collect vertices on the diameter path A--B
    vector<pair<int, int>> path; // (dA[node], node)
    for (int i = 1; i <= n; ++i) {
        if (dA[i] + dB[i] == dAB) {
            path.emplace_back(dA[i], i);
        }
    }
    sort(path.begin(), path.end());
    int k = path.size(); // number of vertices on the path
    vector<int> path_nodes(k), path_dA(k);
    for (int i = 0; i < k; ++i) {
        path_dA[i] = path[i].first;
        path_nodes[i] = path[i].second;
    }

    // Step 5: for each vertex determine its attachment point on the path
    vector<int> cnt(k, 0);
    for (int u = 1; u <= n; ++u) {
        int du_path = (dA[u] + dB[u] - dAB) / 2;
        int dA_proj = dA[u] - du_path;
        // binary search for the closest path vertex in terms of dA
        int idx = lower_bound(path_dA.begin(), path_dA.end(), dA_proj) - path_dA.begin();
        if (idx == k) idx = k - 1;
        if (idx > 0 && abs(path_dA[idx] - dA_proj) > abs(path_dA[idx-1] - dA_proj)) {
            idx = idx - 1;
        }
        cnt[idx]++;
    }

    // Step 6: prefix sums of cnt
    vector<long long> pref(k + 1, 0);
    for (int i = 0; i < k; ++i) {
        pref[i + 1] = pref[i] + cnt[i];
    }

    // Step 7: binary search for the centroid on the path
    int lo = 0, hi = k - 1, cent_idx = -1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        long long left = pref[mid];               // nodes attached strictly before mid
        long long right = n - pref[mid] - cnt[mid]; // nodes attached strictly after mid
        if (left > n / 2) {
            lo = mid + 1;
        } else if (right > n / 2) {
            hi = mid - 1;
        } else {
            cent_idx = mid;
            break;
        }
    }

    // We are guaranteed to find exactly one such index
    int centroid = path_nodes[cent_idx];
    cout << "! " << centroid << endl;

    return 0;
}