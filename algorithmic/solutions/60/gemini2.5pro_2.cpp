#include <iostream>

const int W = 100000;
const double EPS = 1e-7;

// Helper function to perform a query
double do_query(int x1, int y1, int x2, int y2) {
    std::cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << std::endl;
    double response;
    std::cin >> response;
    return response;
}

// Binary search for the minimum x-coordinate of the disk's bounding box
int find_min_x() {
    int low = 0, high = W;
    int ans = W + 1;
    while(low <= high) {
        int mid = low + (high - low) / 2;
        if (do_query(mid, 0, mid, W) > EPS) {
            ans = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }
    return ans;
}

// Binary search for the maximum x-coordinate of the disk's bounding box
int find_max_x(int low_bound) {
    int low = low_bound, high = W;
    int ans = low_bound;
    while(low <= high) {
        int mid = low + (high - low) / 2;
        if (do_query(mid, 0, mid, W) > EPS) {
            ans = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    return ans;
}

// Binary search for the minimum y-coordinate of the disk's bounding box
int find_min_y() {
    int low = 0, high = W;
    int ans = W + 1;
    while(low <= high) {
        int mid = low + (high - low) / 2;
        if (do_query(0, mid, W, mid) > EPS) {
            ans = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }
    return ans;
}

// Binary search for the maximum y-coordinate of the disk's bounding box
int find_max_y(int low_bound) {
    int low = low_bound, high = W;
    int ans = low_bound;
    while(low <= high) {
        int mid = low + (high - low) / 2;
        if (do_query(0, mid, W, mid) > EPS) {
            ans = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    return ans;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int x_left = find_min_x();
    int x_right = find_max_x(x_left);
    int y_bottom = find_min_y();
    int y_top = find_max_y(y_bottom);

    int cx = (x_left + x_right) / 2;
    int cy = (y_bottom + y_top) / 2;
    int r = (x_right - x_left) / 2;

    std::cout << "answer " << cx << " " << cy << " " << r << std::endl;

    return 0;
}