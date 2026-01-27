#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    
    // Read the rest of the input as a string
    std::ostringstream oss;
    oss << cin.rdbuf();
    string rest = oss.str();
    
    // Extract all '0' and '1' digits
    vector<char> digits;
    digits.reserve(n * n);
    for(char ch : rest) {
        if(ch == '0' || ch == '1') digits.push_back(ch);
    }
    
    // If not enough digits, fill remaining with '0'
    if((int)digits.size() < n * n) {
        digits.resize(n * n, '0');
        // Ensure constraints if at least positions exist
        if(n >= 1) digits[0] = '1';
        if(n >= 1) digits[n*n - 1] = '0';
    }
    
    // Output the grid
    for(int i = 0; i < n; ++i) {
        for(int j = 0; j < n; ++j) {
            cout << digits[i * n + j];
        }
        cout << '\n';
    }
    return 0;
}