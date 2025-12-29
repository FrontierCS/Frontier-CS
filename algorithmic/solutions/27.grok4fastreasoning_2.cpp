#include <bits/stdc++.h>
using namespace std;

vector<pair<int,int>> construct(int nrows, int ncols) {
    long long best_k = -1;
    int best_b = 0;
    int maxb = min(nrows, (int)(sqrt(8.0 * ncols + 1) + 10));
    for(int bb = 1; bb <= maxb && bb <= nrows; ++bb) {
        long long bp = (long long) bb * (bb - 1) / 2;
        long long np = min(bp, (long long) ncols);
        long long this_k = (long long) ncols + np + nrows - bb;
        if(this_k > best_k) {
            best_k = this_k;
            best_b = bb;
        }
    }
    int b = best_b;
    long long bp = (long long) b * (b - 1) / 2;
    long long num_pair = min(bp, (long long) ncols);
    long long num_extra = ncols - num_pair;
    vector<pair<int,int>> pos;
    int col_id = 1;
    bool broke = false;
    for(int i = 1; i <= b && !broke; ++i) {
        for(int j = i + 1; j <= b; ++j) {
            if(col_id > num_pair) {
                broke = true;
                break;
            }
            pos.emplace_back(i, col_id);
            pos.emplace_back(j, col_id);
            ++col_id;
        }
    }
    int extra_start = num_pair + 1;
    for(long long e = 0; e < num_extra; ++e) {
        int r = 1 + (e % b);
        int c = extra_start + (int)e;
        pos.emplace_back(r, c);
    }
    for(int r = b + 1; r <= nrows; ++r) {
        int c = 1;
        pos.emplace_back(r, c);
    }
    return pos;
}

int main() {
    int n, m;
    cin >> n >> m;
    auto vec1 = construct(n, m);
    long long k1 = vec1.size();
    auto vec2 = construct(m, n);
    long long k2 = vec2.size();
    vector<pair<int,int>> chosen;
    if(k1 >= k2) {
        chosen = vec1;
    } else {
        for(auto p : vec2) {
            chosen.emplace_back(p.second, p.first);
        }
    }
    cout << chosen.size() << endl;
    for(auto [r, c] : chosen) {
        cout << r << " " << c << endl;
    }
    return 0;
}