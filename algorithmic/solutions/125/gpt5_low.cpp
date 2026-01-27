#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long N;
    if(!(cin >> N)) return 0;
    for(long long i = 1; i <= 2*N; i += 2) {
        cout << "! " << i << " " << i+1 << "\n";
        cout.flush();
    }
    return 0;
}