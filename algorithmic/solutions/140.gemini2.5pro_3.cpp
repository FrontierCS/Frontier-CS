#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <map>

using namespace std;

long long b;
int k;
int w;

using Point = pair<long long, long long>;
using FreqMap = map<long long, int>;

void query(int d, const vector<Point>& probes, FreqMap& counts) {
    cout << "? " << d;
    for (const auto& p : probes) {
        cout << " " << p.first << " " << p.second;
    }
    cout << endl;

    counts.clear();
    for (int i = 0; i < k * d; ++i) {
        long long dist;
        cin >> dist;
        counts[dist]++;
    }
}

bool solve(FreqMap& counts, vector<Point>& solution) {
    if (counts.empty()) {
        return true;
    }

    auto it = counts.begin();
    long long dc = it->first;
    if (it->second == 1) {
        counts.erase(it);
    } else {
        it->second--;
    }

    long long target_sum = 2 * dc + 2 * b;

    vector<long long> keys;
    for(auto const& [key, val] : counts) {
        keys.push_back(key);
    }

    for (long long da : keys) {
        if (counts.count(da) == 0 || counts[da] == 0) continue;
        
        counts[da]--;

        long long db = target_sum - da;
        if (counts.count(db) && counts[db] > 0) {
            counts[db]--;

            long long val_for_abs_v = da - (dc + b);
            long long abs_v = abs(val_for_abs_v);
            long long abs_u = dc - abs_v;

            if (abs_u >= 0 && abs_v <= b && abs_u <= b) {
                // Case 1: v = abs_v
                solution.push_back({abs_v, abs_u});
                if (solve(counts, solution)) {
                    return true;
                }
                solution.pop_back();

                // Case 2: v = -abs_v (if non-zero)
                if (abs_v != 0) {
                    solution.push_back({-abs_v, abs_u});
                    if (solve(counts, solution)) {
                        return true;
                    }
                    solution.pop_back();
                }
            }
            counts[db]++;
        }
        counts[da]++;
    }

    counts[dc]++;
    return false;
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> b >> k >> w;

    // Wave 1: Find (x, |y|) for all deposits
    vector<Point> probes_x = {{-b, 0}, {b, 0}, {0, 0}};
    FreqMap counts_x;
    query(3, probes_x, counts_x);
    vector<Point> solutions_x;
    solve(counts_x, solutions_x);

    // Wave 2: Find (y, |x|) for all deposits
    vector<Point> probes_y = {{0, -b}, {0, b}, {0, 0}};
    FreqMap counts_y;
    query(3, probes_y, counts_y);
    vector<Point> solutions_y;
    solve(counts_y, solutions_y);

    // Combine results
    map<Point, vector<long long>> y_options;
    for (const auto& p : solutions_y) { // p is (y, |x|)
        long long y_val = p.first;
        long long abs_x_val = p.second;
        y_options[{abs_x_val, abs(y_val)}].push_back(y_val);
    }

    vector<Point> final_deposits;
    for (const auto& p : solutions_x) { // p is (x, |y|)
        long long x_val = p.first;
        long long abs_y_val = p.second;
        Point key = {abs(x_val), abs_y_val};
        long long y_val = y_options[key].back();
        y_options[key].pop_back();
        final_deposits.push_back({x_val, y_val});
    }

    cout << "!";
    for (const auto& p : final_deposits) {
        cout << " " << p.first << " " << p.second;
    }
    cout << endl;

    return 0;
}