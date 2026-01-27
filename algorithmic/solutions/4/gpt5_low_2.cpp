#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n, k;
    if(!(cin >> n >> k)) return 0;
    vector<long long> a;
    a.reserve((size_t)n * (size_t)n);
    for(long long i = 0; i < n * n; ++i){
        long long v;
        cin >> v;
        a.push_back(v);
    }
    nth_element(a.begin(), a.begin() + (k - 1), a.end());
    cout << a[k - 1] << "\n";
    return 0;
}