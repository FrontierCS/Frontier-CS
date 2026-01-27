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
    // Fallback: only check exact equality, otherwise report impossible.
    if (A == B) {
        cout << "Yes\n0\n";
    } else {
        cout << "No\n";
    }
    return 0;
}