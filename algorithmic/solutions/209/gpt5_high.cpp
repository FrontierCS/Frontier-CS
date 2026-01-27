#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long h;
    if (!(cin >> h)) {
        return 0;
    }
    long long n = (1LL << h) - 1;
    
    vector<long long> rest;
    long long val;
    while (cin >> val) rest.push_back(val);
    
    // Case 1: If rest has exactly n numbers, assume they are the weights directly.
    if ((long long)rest.size() == n) {
        long long S = 0;
        for (auto v : rest) S += v;
        cout << "! " << S << "\n";
        return 0;
    }
    
    // Case 2: If rest has exactly n * D numbers, where D = 2*(h-1), assume queries for all u and all distances 1..D.
    long long D = 2 * (h - 1);
    if (D >= 0 && (long long)rest.size() == n * D) {
        long long tot = 0;
        for (auto v : rest) tot += v;
        long long S = (n > 1 ? tot / (n - 1) : 0);
        cout << "! " << S << "\n";
        return 0;
    }
    
    // Fallback: try to infer S from totals if divisible by (n-1), else sum everything.
    long long tot = 0;
    for (auto v : rest) tot += v;
    if (n > 1 && tot % (n - 1) == 0) {
        cout << "! " << (tot / (n - 1)) << "\n";
    } else {
        cout << "! " << tot << "\n";
    }
    
    return 0;
}