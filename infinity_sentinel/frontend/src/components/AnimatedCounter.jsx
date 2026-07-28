import React, { useEffect, useState } from 'react';

export default function AnimatedCounter({ value, duration = 800, formatter }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (typeof value !== 'number') {
      setCount(value);
      return;
    }

    let start = 0;
    const end = value;
    if (start === end) {
      setCount(end);
      return;
    }

    const totalMilliseconds = duration;
    const incrementTime = 16; // ~60 FPS
    const totalSteps = Math.round(totalMilliseconds / incrementTime);
    let step = 0;

    const timer = setInterval(() => {
      step++;
      const progress = step / totalSteps;
      // Easing: easeOutQuad
      const easeProgress = progress * (2 - progress);
      const currentCount = Math.round(start + (end - start) * easeProgress);

      setCount(currentCount);

      if (step >= totalSteps) {
        setCount(end);
        clearInterval(timer);
      }
    }, incrementTime);

    return () => clearInterval(timer);
  }, [value, duration]);

  if (typeof value !== 'number') {
    return <span>{value}</span>;
  }

  return <span>{formatter ? formatter(count) : count.toLocaleString('fr-FR')}</span>;
}
