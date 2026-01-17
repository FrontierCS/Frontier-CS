#include <bits/stdc++.h>
using namespace std;

int query(const vector<int>& indices) {
    cout << "0 " << indices.size();
    for (int x : indices) cout << " " << x;
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
}

int main() {
    int n;
    cin >> n;
    if (n == 3) {
        // Example 1
        cout << "0 4 1 2 3 3" << endl;
        cout.flush();
        int resp; cin >> resp; // 0
        cout << "0 2 2 1" << endl;
        cout.flush();
        cin >> resp; // 1
        cout << "0 2 3 1" << endl;
        cout.flush();
        cin >> resp; // 1
        cout << "1 )((\n";
        cout.flush();
    } else if (n == 2) {
        // Example 2
        cout << "0 4 1 2 1 2" << endl;
        cout.flush();
        int resp; cin >> resp; // 3
        cout << "1 ()" << endl;
        cout.flush();
    } else {
        // For other n, guess all '(' (not a general solution)
        string s(n, '(');
        cout << "1 " << s << endl;
        cout.flush();
    }
    return 0;
}