export const latLonToVector3 = (THREE, lat, lon, radius) => {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = radius * Math.sin(phi) * Math.sin(theta);
    const y = radius * Math.cos(phi);
    return new THREE.Vector3(x, y, z);
};
export const createArcCurve = (THREE, start, end, options = {}) => {
    const lift = options.lift ?? 0.24;
    const midpoint = start.clone().add(end).multiplyScalar(0.5);
    const midLength = midpoint.length();
    if (midLength > 0) {
        midpoint.normalize().multiplyScalar(midLength * (1 + lift));
    }
    return new THREE.CatmullRomCurve3([start.clone(), midpoint, end.clone()], false, "catmullrom", 0.5);
};
export const createSphereMesh = (THREE, radius, widthSegments, heightSegments, material) => {
    return new THREE.Mesh(new THREE.SphereGeometry(radius, widthSegments, heightSegments), material);
};
//# sourceMappingURL=primitives.js.map