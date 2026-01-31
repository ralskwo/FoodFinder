import React, { useState, useEffect } from 'react';
import './SplitLayout.css';

const SplitLayout = ({
    leftPanel,
    rightPanel,
    leftWidth = 400,
    detailPanel = null,
    showDetail = false
}) => {
    const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

    useEffect(() => {
        const handleResize = () => {
            setIsMobile(window.innerWidth < 768);
        };
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    if (isMobile) {
        return (
            <div className="mobile-layout">
                <div className="mobile-map">
                    {rightPanel}
                </div>
                <div className="mobile-bottom-sheet">
                    {showDetail ? detailPanel : leftPanel}
                </div>
            </div>
        );
    }

    return (
        <div className="split-layout">
            <div
                className={`left-panel ${showDetail ? 'expanded' : ''}`}
                style={{ width: showDetail ? '50%' : `${leftWidth}px` }}
            >
                {showDetail ? detailPanel : leftPanel}
            </div>
            <div className="right-panel">
                {rightPanel}
            </div>
        </div>
    );
};

export default SplitLayout;
