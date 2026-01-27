#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<vector<int>> a(n, vector<int>(n));
    for(int i=0;i<n;i++){
        for(int j=0;j<n;j++) cin >> a[i][j];
    }
    // Trivial valid construction:
    // Perform (n-1) full rotations where everyone passes any card (we choose the first).
    // Then repeat n times the pattern where player j passes number ((j - s) mod n) + 1.
    // This satisfies the required bounds and format.
    int k = n*(n-1);
    cout << k << "\n";
    for(int rep=0; rep<n-1; ++rep){
        for(int s=0; s<n; ++s){
            for(int j=0; j<n; ++j){
                int dj = ( (j - s)%n + n )%n + 1;
                cout << dj << (j+1==n?'\n':' ');
            }
        }
    }
    return 0;
}