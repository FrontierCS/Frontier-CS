#include <bits/stdc++.h>
using namespace std;

int main() {
    long long n;
    cin >> n;
    long long low_b = 1, high_b = n;
    while (low_b < high_b) {
        long long mid_b = low_b + (high_b - low_b + 1) / 2;
        long long low_a = 1, high_a = n;
        bool got_two = false;
        while (low_a <= high_a) {
            long long mid_a = low_a + (high_a - low_a) / 2;
            cout << mid_a << " " << mid_b << endl;
            int r;
            cin >> r;
            if (r == 0) {
                return 0;
            } else if (r == 2) {
                got_two = true;
                break;
            } else if (r == 1) {
                low_a = mid_a + 1;
            } else if (r == 3) {
                high_a = mid_a - 1;
            }
        }
        if (got_two) {
            low_b = mid_b + 1;
        } else {
            high_b = mid_b - 1;
        }
    }
    long long b_val = low_b;
    long long low_a = 1, high_a = n;
    while (low_a <= high_a) {
        long long mid_a = low_a + (high_a - low_a) / 2;
        cout << mid_a << " " << b_val << endl;
        int r;
        cin >> r;
        if (r == 0) {
            return 0;
        } else if (r == 1) {
            low_a = mid_a + 1;
        } else if (r == 3) {
            high_a = mid_a - 1;
        }
    }
    return 0;
}