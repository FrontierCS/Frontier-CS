#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <numeric>
#include <algorithm>
#include <map>
#include <queue>

using namespace std;

using ld = long double;

int N;
const ld X = 400000.0L;
const ld EPS = 1e-9L;
const ld SLOPE_THRESHOLD = 1e-6L;

map<ld, ld> memo;

// Function to issue a query to the judge
ld do_query(ld x, ld y) {
    cout << "? " << fixed << setprecision(10) << x << " " << y << endl;
    ld dist_sum;
    cin >> dist_sum;
    return dist_sum;
}

// Get S(k) = D(X, kX)/X, with memoization
ld get_S(ld k) {
    if (memo.count(k)) {
        return memo[k];
    }
    ld val = do_query(X, k * X) / X;
    return memo[k] = val;
}

// Function to calculate slope at a point k
ld get_slope(ld k) {
    return (get_S(k + EPS) - get_S(k - EPS)) / (2.0L * EPS);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N;
    
    vector<ld> kinks;
    queue<pair<ld, ld>> q;

    // The range for a_i is [-10000, 10000].
    // k* = a_i + b_i/X. With X=400000, b_i/X is in [-0.025, 0.025].
    // So k* range is roughly [-10000.025, 10000.025]. Search in a slightly larger range.
    q.push({-10000.5L, 10000.5L});

    while (!q.empty() && kinks.size() < N) {
        pair<ld, ld> interval = q.front();
        q.pop();
        ld l = interval.first;
        ld r = interval.second;

        if (kinks.size() + q.size() >= N) {
            kinks.push_back((l + r) / 2.0L);
            continue;
        }

        ld m = l + (r - l) / 2.0L;
        
        ld slope_l = get_slope(l);
        ld slope_m = get_slope(m);
        ld slope_r = get_slope(r);
        
        if (abs(slope_m - slope_l) >= SLOPE_THRESHOLD) {
            q.push({l, m});
        }
        if (abs(slope_r - slope_m) >= SLOPE_THRESHOLD) {
            q.push({m, r});
        }
    }
    
    while(!q.empty()){
        pair<ld, ld> interval = q.front(); q.pop();
        kinks.push_back((interval.first + interval.second) / 2.0L);
    }
    
    vector<long long> a(N), b(N);
    sort(kinks.begin(), kinks.end());
    
    for (int i = 0; i < N; ++i) {
        ld k_star = kinks[i];
        a[i] = round(k_star);
        b[i] = round(X * (k_star - a[i]));
    }

    cout << "!";
    for (int i = 0; i < N; ++i) cout << " " << a[i];
    for (int i = 0; i < N; ++i) cout << " " << b[i];
    cout << endl;

    return 0;
}