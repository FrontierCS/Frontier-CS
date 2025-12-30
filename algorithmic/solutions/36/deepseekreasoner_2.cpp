#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    long long total_cost = 0;
    long long low = 1, high = 2;
    // Exponential search for an upper bound
    while (total_cost + high <= 1000000) {
        cout << 0 << " " << high;
        for (long long i = 1; i <= high; ++i) {
            cout << " " << i;
        }
        cout << endl;
        cout.flush();
        total_cost += high;
        int collisions;
        cin >> collisions;
        if (collisions > 0) {
            break;
        }
        low = high;
        high *= 2;
        if (high > 2000000000) high = 2000000000;
    }
    // Binary search between low and high
    long long ans = low;
    while (low < high && total_cost + (low + (high - low)/2) <= 1000000) {
        long long mid = low + (high - low) / 2;
        cout << 0 << " " << mid;
        for (long long i = 1; i <= mid; ++i) {
            cout << " " << i;
        }
        cout << endl;
        cout.flush();
        total_cost += mid;
        int collisions;
        cin >> collisions;
        if (collisions > 0) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    ans = low;
    cout << 1 << " " << ans << endl;
    cout.flush();
    return 0;
}