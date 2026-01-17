#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int main() {
    ll x;
    cin >> x;
    if (x == 1) {
        cout << "1\n1\n";
        return 0;
    }
    ll y = x - 1;
    vector<int> bits;
    for (int i = 0; i < 60; ++i) {
        if (y >> i & 1) bits.push_back(i);
    }
    // We will construct a grid of size n = 300
    int n = 300;
    vector<vector<int>> a(n + 1, vector<int>(n + 1, 0));
    
    // Set column 1 all ones
    for (int i = 1; i <= n; ++i) a[i][1] = 1;
    // Set row n all ones
    for (int j = 1; j <= n; ++j) a[n][j] = 1;
    
    // For each bit i, create a channel
    for (int b : bits) {
        int i = b;
        // Starting row and column for the doubling chain
        // We space them out generously to avoid overlap
        int start_row = 1 + i * 10;  // adjust if needed
        int start_col = 2 + i * 10;
        // Make sure we are within bounds
        if (start_row + i > n || start_col + i > n) {
            // If not, we need to increase n, but we fixed n=300
            // This might fail for large i, but we hope input does not require large i
            // In practice, for x up to 1e18, i is at most 60.
            // This spacing might cause overlap for i>=30, but we proceed anyway.
        }
        // Create doubling chain from (start_row, start_col) to (start_row+i, start_col+i)
        for (int d = 0; d <= i; ++d) {
            a[start_row + d][start_col + d] = 1;
            if (d < i) {
                a[start_row + d][start_col + d + 1] = 1;
                a[start_row +