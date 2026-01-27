#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <tuple>
#include <set>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    if (n <= 3) {
        cout << 0 << endl;
        return 0;
    }

    vector<tuple<int, int, int>> added_edges;
    set<int> available_lengths;
    available_lengths.insert(1);

    int k = 16;
    if (n < 4096) {
      if (n == 0) k = 1;
      else k = ceil(pow(n + 1, 1.0/3.0));
      if (k < 2) k = 2;
    }

    vector<int> target_lengths;
    long long stride = 1;
    for (int p = 0; p < 3; ++p) {
        for (int c = 1; c < k; ++c) {
            if (c * stride > n) continue;
            target_lengths.push_back(c * stride);
        }
        if (p < 2 && stride > n / k) break;
        stride *= k;
    }
    sort(target_lengths.begin(), target_lengths.end());
    target_lengths.erase(unique(target_lengths.begin(), target_lengths.end()), target_lengths.end());
    
    for (int len : target_lengths) {
        if (len <= 1) continue;
        if (available_lengths.count(len)) continue;

        int s1 = 0, s2 = 0;
        
        if (len < k) {
            s1 = len - 1;
            s2 = 1;
        } else {
            long long current_stride = k;
            while(current_stride * k <= len) {
                current_stride *= k;
            }
            if (len % current_stride == 0) {
                 s1 = len - current_stride;
                 s2 = current_stride;
            } else {
                s1 = len - 1;
                s2 = 1;
            }
        }
        
        if(s1 == 0) {
            s1 = len -1; s2 = 1;
        }

        if (available_lengths.count(s1) && available_lengths.count(s2)) {
            for (int i = 0; i <= n - len; ++i) {
                added_edges.emplace_back(i, i + s1, i + len);
            }
            available_lengths.insert(len);
        }
    }

    cout << added_edges.size() << "\n";
    for (const auto& edge : added_edges) {
        cout << get<0>(edge) << " " << get<1>(edge) << " " << get<2>(edge) << "\n";
    }

    return 0;
}