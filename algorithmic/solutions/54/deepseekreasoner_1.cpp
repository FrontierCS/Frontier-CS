#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int main() {
    int n;
    cin >> n;
    vector<int> dist1(n+1, 0), dist2(n+1, 0);
    
    // Query distances from node 1 to all others
    for (int i = 2; i <= n; ++i) {
        cout << "? 1 " << i << endl;
        cout.flush();
        cin >> dist1[i];
    }
    dist1[1] = 0;
    
    // Find a node farthest from node 1
    int a = 1;
    for (int i = 2; i <= n; ++i) {
        if (dist1[i] > dist1[a]) a = i;
    }
    
    // Query distances from node a to all others
    for (int i = 1; i <= n; ++i) {
        if (i == a) continue;
        cout << "? " << a << " " << i << endl;
        cout.flush();
        cin >> dist2[i];
    }
    dist2[a] = 0;
    
    int d_ra = dist1[a];   // distance between 1 and a
    vector<int> s(n+1), t(n+1);
    ll total_s = 0;
    int L = d_ra;
    vector<int> cnt(L+1, 0);
    
    // Compute s[u] and t[u] for each node u
    for (int u = 1; u <= n; ++u) {
        int dr = dist1[u];
        int da = dist2[u];
        int sum = dr + da - d_ra;
        s[u] = sum / 2;
        total_s += s[u];
        t[u] = (dr - da + d_ra) / 2;
        cnt[t[u]]++;
    }
    
    // Prefix sums for quick computation of sum |t - t_u|
    vector<ll> pref_cnt(L+1, 0), pref_sum_t(L+1, 0);
    for (int i = 0; i <= L; ++i) {
        pref_cnt[i] = (i > 0 ? pref_cnt[i-1] : 0) + cnt[i];
        pref_sum_t[i] = (i > 0 ? pref_sum_t[i-1] : 0) + (ll)i * cnt[i];
    }
    ll total_sum_t = pref_sum_t[L];
    
    // Find t that minimizes S(t) = total_s + sum |t - t_u|
    ll best_S = 1e18;
    int best_t = -1;
    for (int t_val = 0; t_val <= L; ++t_val) {
        ll left_cnt = (t_val > 0 ? pref_cnt[t_val-1] : 0);
        ll left_sum = (t_val > 0 ? pref_sum_t[t_val-1] : 0);
        ll right_cnt = n - pref_cnt[t_val];
        ll right_sum = total_sum_t - pref_sum_t[t_val];
        ll sum_abs = t_val * left_cnt - left_sum + (right_sum - t_val * right_cnt);
        ll S = total_s + sum_abs;
        if (S < best_S) {
            best_S = S;
            best_t = t_val;
        }
    }
    
    // The centroid is the node on the path with s=0 and t = best_t
    int centroid = -1;
    for (int u = 1; u <= n; ++u) {
        if (s[u] == 0 && t[u] == best_t) {
            centroid = u;
            break;
        }
    }
    
    cout << "! " << centroid << endl;
    cout.flush();
    return 0;
}