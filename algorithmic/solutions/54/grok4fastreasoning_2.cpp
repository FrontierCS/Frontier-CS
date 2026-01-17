#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n;
    cin >> n;
    int m = n / 2;
    vector<int> dist_start(n + 1, 0);
    for (int i = 2; i <= n; ++i) {
        cout << "? 1 " << i << '\n';
        cout.flush();
        cin >> dist_start[i];
    }
    int uu = 1;
    int maxd = 0;
    for (int i = 1; i <= n; ++i) {
        if (dist_start[i] > maxd) {
            maxd = dist_start[i];
            uu = i;
        }
    }
    vector<int> distu(n + 1, 0);
    if (uu == 1) {
        distu = dist_start;
    } else {
        distu[uu] = 0;
        distu[1] = dist_start[uu];
        for (int i = 2; i <= n; ++i) {
            if (i != uu) {
                cout << "? " << uu << " " << i << '\n';
                cout.flush();
                cin >> distu[i];
            }
        }
    }
    int vv = uu;
    int maxdu = 0;
    for (int i = 1; i <= n; ++i) {
        if (distu[i] > maxdu) {
            maxdu = distu[i];
            vv = i;
        }
    }
    int D = maxdu;
    vector<int> distv(n + 1, 0);
    bool need_query_v = true;
    if (vv == 1) {
        distv = dist_start;
        need_query_v = false;
    } else if (vv == uu) {
        distv = distu;
        need_query_v = false;
    }
    if (need_query_v) {
        distv[vv] = 0;
        if (1 != vv) distv[1] = dist_start[vv];
        if (uu != vv) distv[uu] = distu[vv];
        for (int i = 1; i <= n; ++i) {
            if (i != vv && i != 1 && i != uu) {
                cout << "? " << vv << " " << i << '\n';
                cout.flush();
                cin >> distv[i];
            }
        }
    }
    vector<int> onpath;
    for (int i = 1; i <= n; ++i) {
        if (distu[i] + distv[i] == D) {
            onpath.push_back(i);
        }
    }
    sort(onpath.begin(), onpath.end(), [&](int a, int b) {
        return distu[a] < distu[b];
    });
    vector<int> count_pos(D + 1, 0);
    for (int i = 1; i <= n; ++i) {
        int du = distu[i];
        int dv = distv[i];
        int diff = du - dv + D;
        int proj = diff / 2;
        if (proj >= 0 && proj <= D) {
            count_pos[proj]++;
        }
    }
    vector<long long> prefix(D + 2, 0);
    for (int j = 1; j <= D + 1; ++j) {
        prefix[j] = prefix[j - 1] + count_pos[j - 1];
    }
    int centroid_node = -1;
    for (int k = 0; k <= D; ++k) {
        long long lsize = prefix[k];
        long long rsize = (long long)n - prefix[k + 1];
        if (lsize <= m && rsize <= m) {
            centroid_node = onpath[k];
            break;
        }
    }
    cout << "! " << centroid_node << '\n';
    cout.flush();
    return 0;
}