#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <set>
#include <map>

using namespace std;

long long b;
int k, w;

long long get_sum_dist(long long s, long long t) {
    cout << "? 1 " << s << " " << t << endl;
    long long sum_dist = 0;
    for (int i = 0; i < k; ++i) {
        long long dist;
        cin >> dist;
        sum_dist += dist;
    }
    return sum_dist;
}

// Get number of coordinates greater than val.
// val is in [-b, b].
int get_count_greater(long long val, char dimension) {
    if (val >= b) return 0;

    long long sum1, sum2;
    long long C = 0; // A constant coordinate for the other dimension.

    if (dimension == 'x') {
        sum1 = get_sum_dist(val, C);
        sum2 = get_sum_dist(val + 1, C);
    } else { // dimension == 'y'
        sum1 = get_sum_dist(C, val);
        sum2 = get_sum_dist(C, val + 1);
    }

    return (k + sum1 - sum2) / 2;
}

long long find_jth_coord(int j, char dimension) {
    long long low = -b, high = b;
    long long ans = b;

    while (low <= high) {
        long long mid = low + (high - low) / 2;
        if (get_count_greater(mid, dimension) <= k - j) {
            ans = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }
    return ans;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> b >> k >> w;

    multiset<long long> x_coords, y_coords;

    for (int j = 1; j <= k; ++j) {
        x_coords.insert(find_jth_coord(j, 'x'));
    }

    for (int j = 1; j <= k; ++j) {
        y_coords.insert(find_jth_coord(j, 'y'));
    }
    
    vector<pair<long long, long long>> deposits;

    while (deposits.size() < k) {
        long long x = *x_coords.begin();
        x_coords.erase(x_coords.begin());

        set<long long> distinct_y(y_coords.begin(), y_coords.end());
        
        for (long long y : distinct_y) {
            cout << "? 1 " << x << " " << y << endl;
            bool is_dep = false;
            for (int i = 0; i < k; ++i) {
                long long d;
                cin >> d;
                if (d == 0) {
                    is_dep = true;
                }
            }

            if (is_dep) {
                deposits.push_back({x, y});
                y_coords.erase(y_coords.find(y));
                break;
            }
        }
    }

    cout << "!";
    for (const auto& p : deposits) {
        cout << " " << p.first << " " << p.second;
    }
    cout << endl;

    return 0;
}