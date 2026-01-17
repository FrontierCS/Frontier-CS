#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> a(n+1);
    for (int i=1; i<=n; i++) cin >> a[i];
    
    int x;
    if (n <= 3) x = 1;
    else x = 3;
    
    vector<int> arr = a;
    vector<int> pos(n+1);
    for (int i=1; i<=n; i++) pos[arr[i]] = i;
    
    vector<pair<int,int>> ops;
    
    auto rev = [&](int l, int r) {
        for (int a=l, b=r; a < b; a++, b--) {
            swap(arr[a], arr[b]);
            pos[arr[a]] = a;
            pos[arr[b]] = b;
        }
    };
    
    for (int i=1; i<=n; i++) {
        while (pos[i] > i) {
            int p = pos[i];
            if (p - i >= 3) {
                int l = p-3, r = p;
                rev(l, r);
                ops.push_back({l, r});
            } else {
                int l = p-1, r = p;
                rev(l, r);
                ops.push_back({l, r});
            }
        }
    }
    
    cout << x << "\n";
    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    
    return 0;
}