#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

using namespace std;

long long query(int n, const vector<int>& a) {
    cout << "? " << n;
    for (int x : a) {
        cout << " " << x;
    }
    cout << endl;
    long long response;
    cin >> response;
    return response;
}

long long calculate_lines(long long W, int n, const vector<int>& a) {
    if (W <= 0) return 1e18; 
    long long max_a = 0;
    for(int x : a) {
        if (x > max_a) {
            max_a = x;
        }
    }
    if (max_a > W) {
        return 0;
    }
    long long lines = 1;
    long long current_sum = 0;
    for (int x : a) {
        if (current_sum == 0) {
            current_sum = x;
        } else if (current_sum + x <= W) {
            current_sum += x;
        } else {
            lines++;
            current_sum = x;
        }
    }
    return lines;
}

void solve() {
    int n1 = 350;
    vector<int> a1(n1);
    iota(a1.begin(), a1.end(), 1);
    long long L1 = query(n1, a1);
    
    if (L1 == 0) {
        // W < 350. We have one query left.
        // Binary search for the largest value that doesn't fail.
        int low = 1, high = n1 -1, ans_w = 1;
        while(low <= high) {
            int mid = low + (high - low) / 2;
            vector<int> temp_a(1, mid);
            if(query(1, temp_a) == 1) { // W >= mid
                ans_w = mid;
                low = mid + 1;
            } else { // W < mid
                high = mid - 1;
            }
        }
        cout << "! " << ans_w << endl;
        return;
    }

    long long low = 1, high = 100000;
    long long W_min = -1, W_max = -1;
    
    long long search_high = high;
    while(low <= high) {
        long long mid = low + (high - low) / 2;
        long long lines = calculate_lines(mid, n1, a1);
        if (lines != 0 && lines <= L1) {
            W_min = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }
    
    low = W_min, high = search_high;
    while(low <= high) {
        long long mid = low + (high - low) / 2;
        if (calculate_lines(mid, n1, a1) == L1) {
            W_max = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    
    if (W_min == W_max) {
        cout << "! " << W_min << endl;
        return;
    }
    
    int n2 = 10000;
    vector<int> a2;
    if (W_min > 1) {
        a2.push_back(W_min - 1);
    }
    for(int i = a2.size(); i < n2; ++i) {
        a2.push_back(1);
    }
    n2 = a2.size();
    
    long long L2 = query(n2, a2);

    low = W_min, high = W_max;
    long long final_W = W_min;

    while (low <= high) {
        long long mid = low + (high - low) / 2;
        long long lines = calculate_lines(mid, n2, a2);
        if (lines >= L2) {
            final_W = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    cout << "! " << final_W << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.flush();
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}