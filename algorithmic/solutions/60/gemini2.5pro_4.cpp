#include <iostream>
#include <cmath>
#include <iomanip>

using namespace std;

const int MAX_COORD = 100000;
const double EPS = 1e-4;

// Function to perform a query and get the response
double ask(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    double response;
    cin >> response;
    return response;
}

// Generic binary search to find the first integer `x` for which pred(x) is true
template<typename Predicate>
int find_first_true(Predicate pred) {
    int low = 0, high = MAX_COORD;
    while (low < high) {
        int mid = low + (high - low) / 2;
        if (pred(mid)) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    return low;
}

// Generic binary search to find the last integer `x` for which pred(x) is true
template<typename Predicate>
int find_last_true(Predicate pred) {
    int low = 0, high = MAX_COORD;
    while (low < high) {
        int mid = low + (high - low + 1) / 2;
        if (pred(mid)) {
            low = mid;
        } else {
            high = mid - 1;
        }
    }
    return low;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout << fixed << setprecision(10);

    // Predicate for vertical probes: checks if a vertical line at x intersects the circle
    auto vertical_probe_intersects = [&](int x) {
        return ask(x, 0, x, MAX_COORD) > EPS;
    };
    
    int x_min = find_first_true(vertical_probe_intersects);
    int x_max = find_last_true(vertical_probe_intersects);

    // Predicate for horizontal probes: checks if a horizontal line at y intersects the circle
    auto horizontal_probe_intersects = [&](int y) {
        return ask(0, y, MAX_COORD, y) > EPS;
    };

    int y_min = find_first_true(horizontal_probe_intersects);
    int y_max = find_last_true(horizontal_probe_intersects);
    
    // Calculate center and radius from the bounding box
    int cx = (x_min + x_max) / 2;
    int cy = (y_min + y_max) / 2;
    int r = (x_max - x_min) / 2;
    
    // Output the final answer
    cout << "answer " << cx << " " << cy << " " << r << endl;

    return 0;
}