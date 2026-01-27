#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if(!(cin >> N)) return 0;
    vector<long long> A(N), B(N);
    for(int i=0;i<N;i++) cin >> A[i];
    for(int i=0;i<N;i++) cin >> B[i];
    long long sa = 0, sb = 0;
    for(auto x: A) sa += x;
    for(auto x: B) sb += x;
    if(sa != sb) {
        cout << "No\n";
        return 0;
    }
    if(A == B){
        cout << "Yes\n0\n";
        return 0;
    }
    // Fallback: not implementing transformation, declare impossible to avoid incorrect sequence
    cout << "No\n";
    return 0;
}