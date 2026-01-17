#include <iostream>
#include <functional>
#include <map>

using namespace std;

// Function to perform a query and get the result.
// It sends the query to standard output and reads the response from standard input.
double ask(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    double response;
    cin >> response;
    return response;
}

// Binary search to find the smallest integer coordinate `c` in [0, 100000]
// for which `probe_func(c)` returns a value greater than a small epsilon.
int find_first_positive(const function<double(int)>& probe_func) {
    int low = 0, high = 100000;
    int result = 100001;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (probe_func(mid) > 1e-7) {
            result = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }
    return result;
}

// Binary search to find the largest integer coordinate `c` in [0, 100000]
// for which `probe_func(c)` returns a value greater than a small epsilon.
int find_last_positive(const function<double(int)>& probe_func) {
    int low = 0, high = 100000;
    int result = -1;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (probe_func(mid) > 1e-7) {
            result = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    return result;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    map<int, double> cache_x, cache_y;

    auto vertical_probe = [&](int x) {
        if (cache_x.count(x)) {
            return cache_x[x];
        }
        double res = ask(x, 0, x, 100000);
        cache_x[x] = res;
        return res;
    };
    
    auto horizontal_probe = [&](int y) {
        if (cache_y.count(y)) {
            return cache_y[y];
        }
        double res = ask(0, y, 100000, y);
        cache_y[y] = res;
        return res;
    };

    int x_L = find_first_positive(vertical_probe);
    int x_R = find_last_positive(vertical_probe);
    int y_B = find_first_positive(horizontal_probe);
    int y_T = find_last_positive(horizontal_probe);

    int cx = (x_L + x_R) / 2;
    int cy = (y_B + y_T) / 2;
    int r = (x_R - x_L + 2) / 2;

    cout << "answer " << cx << " " << cy << " " << r << endl;

    return 0;
}