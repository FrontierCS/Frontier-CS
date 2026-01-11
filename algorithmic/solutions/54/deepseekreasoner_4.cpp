#include <bits/stdc++.h>
using namespace std;

int n;
map<pair<int,int>, int> cache;

int query(int u, int v) {
    if (u == v) return 0;
    if (u > v) swap(u, v);
    auto it = cache.find({u, v});
    if (it != cache.end()) return it->second;
    cout << "? " << u << " " << v << endl;
    cout.flush();
    int d;
    cin >> d;
    cache[{u, v}] = d;
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n;

    // Step 1: choose r=1, get distances, find farthest node a
    vector<int> dist_r(n+1);
    dist_r[1] = 0;
    int a = 1;
    for (int i = 2; i <= n; ++i) {
        dist_r[i] = query(1, i);
        if (dist_r[i] > dist_r[a]) a = i;
    }

    // Step 2: get distances from a, find farthest node b
    vector<int> dist_a(n+1);
    dist_a[a] = 0;
    int b = 1;
    if (b == a) b = 2;
    for (int i = 1; i <= n; ++i) {
        if (i == a) continue;
        dist_a[i] = query(a, i);
        if (dist_a[i] > dist_a[b]) b = i;
    }

    // Step 3: get distances from b
    vector<int> dist_b(n+1);
    dist_b[b] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i == b) continue;
        dist_b[i] = query(b, i);
    }

    int d_ab = dist_a[b]; // distance between a and b

    // Compute L for every node
    vector<int> L(n+1);
    for (int i = 1; i <= n; ++i) {
        L[i] = (dist_a[i] - dist_b[i] + d_ab) / 2;
    }

    // Collect nodes on the a-b path (they satisfy dist_a[i] + dist_b[i] == d_ab)
    vector<int> path;
    for (int i = 1; i <= n; ++i) {
        if (dist_a[i] + dist_b[i] == d_ab) {
            path.push_back(i);
        }
    }
    // Sort by L (which equals dist_a[i] for nodes on the path)
    sort(path.begin(), path.end(), [&](int x, int y) {
        return L[x] < L[y];
    });

    // Precompute sorted list of all L values for quick counting
    vector<int> sorted_L = L;
    sort(sorted_L.begin(), sorted_L.end());

    // Binary search on the path
    int lo = 0, hi = (int)path.size() - 1;
    int centroid = -1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        int x = path[mid];
        int Lx = L[x];

        int cnt_less = lower_bound(sorted_L.begin(), sorted_L.end(), Lx) - sorted_L.begin();
        int cnt_greater = sorted_L.end() - upper_bound(sorted_L.begin(), sorted_L.end(), Lx);

        if (cnt_less > n/2) {
            hi = mid - 1;
        } else if (cnt_greater > n/2) {
            lo = mid + 1;
        } else {
            centroid = x;
            break;
        }
    }
    // In case something went wrong, pick the middle of the path
    if (centroid == -1) {
        centroid = path[path.size() / 2];
    }

    cout << "! " << centroid << endl;
    cout.flush();
    return 0;
}